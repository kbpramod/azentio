"""Member 2 AI Orchestration Pipeline Adapter.

This module provides the stable boundary between Member 1's core FastAPI/database
subsystem and Member 2's AI orchestration engine (Speech-to-Text, Dialogue Policy,
LLM Intent Classification, Grounded Generation, and Text-to-Speech).
"""

import re
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.vaani_models import (
    Account,
    Call,
    ConversationTurn,
    Customer,
    Loan,
    LoanApplication,
    Session,
)
from app.services.audit_service import record_audit_event


async def process_ai_turn(
    db: AsyncSession,
    session: Session,
    call: Call,
    text: str,
    input_type: str = "voice_transcript",
) -> Dict[str, Any]:
    """Callable entry point invoked by POST /api/v1/sessions/{session_id}/turn."""
    clean_text = text.strip()
    lowered = clean_text.lower()

    # Determine turn number
    count_res = await db.execute(
        select(func.count(ConversationTurn.turn_id)).where(ConversationTurn.call_id == call.call_id)
    )
    turn_count = (count_res.scalar() or 0) + 1

    turn_id = f"TURN-{uuid.uuid4().hex[:6].upper()}"
    detected_intents: List[str] = []
    tickets: List[str] = []
    escalation: Optional[str] = None
    reply_text: str = ""

    # Check for in-dialogue verification credentials (e.g. "C1023", "1995-03-12")
    cust_id_match = re.search(r"\b(C\d{3,4})\b", clean_text, re.IGNORECASE)
    dob_match = re.search(r"\b(\d{4}[-/]\d{2}[-/]\d{2})\b", clean_text)

    cand_cust_id = (cust_id_match.group(1).upper() if cust_id_match else None) or session.customer_id
    cand_dob = dob_match.group(1).replace("/", "-") if dob_match else None

    if not session.verified and cand_cust_id and cand_dob:
        try:
            from app.services.verification_service import verify_customer_identity
            verified_session = await verify_customer_identity(db, session.session_id, cand_cust_id, cand_dob)
            session.verified = verified_session.verified
            session.customer_id = cand_cust_id
            session.current_state = "VERIFIED"
            cust_res = await db.execute(select(Customer).where(Customer.customer_id == cand_cust_id))
            customer = cust_res.scalar_one_or_none()
            cust_name = customer.customer_name if customer else cand_cust_id
            detected_intents.append("customer_verification")
            reply_text = (
                f"Thank you, {cust_name}! Your identity has been verified successfully. "
                "You can now ask about your active loans, EMI repayments, loan application status, or account balance."
            )
        except Exception as e:
            detected_intents.append("verification_failure")
            reply_text = f"Verification could not be completed: {str(e)}. Please check your Customer ID and Date of Birth."

    # Gating: Check whether session is verified
    if not reply_text:
        if not session.verified:
            if any(w in lowered for w in ["loan", "balance", "emi", "statement", "schedule", "account", "transfer"]):
                detected_intents.append("unverified_banking_inquiry")
                reply_text = (
                    "For your security, I need to verify your identity before accessing your banking records. "
                    "Please provide your Customer ID (e.g., C1023) and Date of Birth (YYYY-MM-DD) to proceed."
                )
            elif any(w in lowered for w in ["hello", "hi", "hey", "greetings"]):
                detected_intents.append("greeting")
                reply_text = (
                    "Hello! Welcome to Azentio Banking Voice Assistant. "
                    "I can assist you with your loan accounts, EMI repayment schedules, and account details. "
                    "Please state your Customer ID and Date of Birth to access personal accounts, or ask me any general question."
                )
            elif any(w in lowered for w in ["card", "debit"]):
                detected_intents.append("card_inquiry")
                reply_text = "Your Azentio Platinum Debit Card is active with 256-bit encryption. You can view or freeze your card from the dashboard."
            elif any(w in lowered for w in ["transfer", "upi", "send money"]):
                detected_intents.append("transfer_info")
                reply_text = "You can send funds instantly via the Transfer or UPI section in your Azentio dashboard."
            elif any(w in lowered for w in ["credit", "tokens"]):
                detected_intents.append("credits_info")
                reply_text = "You have AI Credits available for voice banking assistant queries."
            elif any(w in lowered for w in ["help", "what can you do"]):
                detected_intents.append("help_inquiry")
                reply_text = (
                    "I can look up your active loan applications, upcoming EMI repayment schedules, "
                    "outstanding loan balances, savings account balance, recent transactions, or escalate your call to a human officer."
                )
            elif any(w in lowered for w in ["human", "agent", "supervisor", "representative"]):
                detected_intents.append("escalation_request")
                escalation = "Customer requested human representative prior to verification."
                reply_text = "I am connecting you with a human banking officer. Please hold while I transfer your call."
            else:
                detected_intents.append("general_inquiry")
                reply_text = (
                    "Thank you for contacting Azentio Banking. "
                    "To review your loans or financial accounts, please provide your Customer ID and Date of Birth."
                )
        else:
            # Verified Session: Ground responses using synthetic database
            customer_id = session.customer_id
            cust_res = await db.execute(select(Customer).where(Customer.customer_id == customer_id))
            customer = cust_res.scalar_one_or_none()
            cust_name = customer.customer_name if customer else "valued customer"

            if any(w in lowered for w in ["application", "apply", "los", "approval", "status of my loan"]):
                detected_intents.append("los_status_query")
                apps_res = await db.execute(
                    select(LoanApplication).where(LoanApplication.customer_id == customer_id)
                )
                apps = apps_res.scalars().all()
                if apps:
                    app_info = apps[0]
                    pending = f"Pending documents: {', '.join(app_info.pending_documents)}." if app_info.pending_documents else "No pending documents required."
                    reply_text = (
                        f"Hello {cust_name}, your {app_info.product_type} loan application ({app_info.application_id}) "
                        f"is currently in '{app_info.application_status}'. {pending}"
                    )
                else:
                    reply_text = f"Hello {cust_name}, you have no active loan applications on file at this time."

            elif any(w in lowered for w in ["loan", "emi", "due", "overdue", "repayment"]):
                detected_intents.append("lms_loan_inquiry")
                loans_res = await db.execute(
                    select(Loan).where(Loan.customer_id == customer_id)
                )
                loans = loans_res.scalars().all()
                if loans:
                    ln = loans[0]
                    reply_text = (
                        f"Hello {cust_name}, on your {ln.product_type} loan ({ln.loan_id}), your outstanding balance is "
                        f"${ln.outstanding_amount:,.2f}. Your next monthly EMI of ${ln.emi_amount:,.2f} is due on {ln.next_due_date}."
                    )
                    if ln.overdue_amount > 0:
                        reply_text += f" Please note an overdue amount of ${ln.overdue_amount:,.2f} is currently pending."
                else:
                    reply_text = f"Hello {cust_name}, our records show no active loan accounts under your profile."

            elif any(w in lowered for w in ["balance", "money", "funds", "checking", "savings"]):
                detected_intents.append("cbs_balance_inquiry")
                acc_res = await db.execute(
                    select(Account).where(Account.customer_id == customer_id)
                )
                accounts = acc_res.scalars().all()
                if accounts:
                    acc = accounts[0]
                    masked_num = f"****{acc.account_number[-4:]}"
                    reply_text = (
                        f"Your {acc.account_type} account ({masked_num}) balance is "
                        f"${acc.balance:,.2f} {acc.currency}."
                    )
                else:
                    reply_text = f"Hello {cust_name}, we found no active accounts associated with your customer ID."

            elif any(w in lowered for w in ["card", "debit"]):
                detected_intents.append("card_inquiry")
                reply_text = f"Hello {cust_name}, your Azentio Platinum Debit Card is active and protected by 256-bit encryption. You can view or freeze your card from the dashboard."

            elif any(w in lowered for w in ["transfer", "upi", "send money"]):
                detected_intents.append("transfer_info")
                reply_text = f"Hello {cust_name}, you can send funds instantly via the Transfer or UPI section in your Azentio dashboard."

            elif any(w in lowered for w in ["human", "agent", "representative", "complaint", "escalate"]):
                detected_intents.append("escalation_request")
                escalation = "Customer requested human supervisor."
                reply_text = (
                    "I understand. I am escalating your request to a customer service specialist. "
                    "A support ticket has been created and an agent will join shortly."
                )
            else:
                detected_intents.append("general_assistant_query")
                reply_text = (
                    f"Hello {cust_name}. Your account is verified and in good standing. "
                    "I can provide your loan application status, upcoming EMI schedules, or account balances. "
                    "How may I help you?"
                )

    # Persist the Conversation Turn in SQLite/PostgreSQL
    turn = ConversationTurn(
        turn_id=turn_id,
        call_id=call.call_id,
        session_id=session.session_id,
        turn_number=turn_count,
        input_type=input_type,
        transcript=clean_text,
        detected_intents=detected_intents,
        reply_text=reply_text,
        processing_status="COMPLETED",
    )
    db.add(turn)

    await record_audit_event(
        db=db,
        event_type="TURN_PROCESSED",
        event_status="SUCCESS",
        session_id=session.session_id,
        call_id=call.call_id,
        metadata={"turn_id": turn_id, "turn_number": turn_count, "intents": detected_intents},
    )

    await db.commit()
    await db.refresh(turn)

    return {
        "turn_id": turn_id,
        "session_id": session.session_id,
        "call_id": call.call_id,
        "turn_number": turn_count,
        "reply_text": reply_text,
        "detected_intents": detected_intents,
        "state": session.current_state,
        "verified": session.verified,
        "tickets": tickets,
        "escalation": escalation,
    }
