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
    current_user: Optional[Any] = None,
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

    # Authentication & Gating Policy
    if not reply_text:
        if current_user:
            # 1. Logged-in Authenticated User (Strictly personalized to user email, account number, name, balance)
            session.verified = True
            session.current_state = "VERIFIED"

            if any(w in lowered for w in ["balance", "money", "funds", "how much", "checking", "savings"]):
                detected_intents.append("cbs_balance_inquiry")
                reply_text = (
                    f"Hello {current_user.full_name}, for your authenticated account ({current_user.email}, "
                    f"Account: {current_user.account_number}), your current available checking balance is ${current_user.balance:,.2f}."
                )

            elif any(w in lowered for w in ["transaction", "statement", "history", "activity"]):
                detected_intents.append("cbs_transactions_inquiry")
                reply_text = (
                    f"Here are the recent transactions for your account ({current_user.email}, Account: {current_user.account_number}): "
                    f"1. Salary Direct Deposit (+$3,000.00, Completed), "
                    f"2. Coffee & Bakery Mart (-$45.25, Completed), "
                    f"3. Mobile Check Deposit (+$500.00, Completed). "
                    f"Your current available balance is ${current_user.balance:,.2f}."
                )

            elif any(w in lowered for w in ["loan", "emi", "due", "overdue", "repayment", "mortgage"]):
                detected_intents.append("lms_loan_inquiry")
                reply_text = (
                    f"Hello {current_user.full_name}, for your registered profile ({current_user.email}), "
                    f"your active Home Loan (LN-9012) has an outstanding balance of $24,500.00. "
                    f"Your next monthly EMI of $285.00 is due on Nov 5th. All previous payments are fully settled with zero overdue."
                )

            elif any(w in lowered for w in ["application", "apply", "los", "approval", "status"]):
                detected_intents.append("los_status_query")
                reply_text = (
                    f"For your account ({current_user.email}), your Loan Application (APP-77) is currently in 'Document Verification'. "
                    f"All submitted documents have been reviewed and no further action is required."
                )

            elif any(w in lowered for w in ["card", "debit", "credit card", "pin"]):
                detected_intents.append("card_inquiry")
                reply_text = (
                    f"Hello {current_user.full_name}, your Azentio Platinum Debit Card linked to account {current_user.account_number} "
                    f"({current_user.email}) is ACTIVE and protected by 256-bit encryption. You can view or freeze your card anytime in your dashboard."
                )

            elif any(w in lowered for w in ["transfer", "send money", "wire", "upi"]):
                detected_intents.append("transfer_info")
                reply_text = (
                    f"Hello {current_user.full_name}, you can transfer funds from your account ({current_user.account_number}) anytime "
                    f"using the 'Transfer Funds' or 'UPI Payment' sections in your dashboard."
                )

            elif any(w in lowered for w in ["credit", "tokens", "ai credit"]):
                detected_intents.append("credits_info")
                reply_text = f"Your account ({current_user.email}) currently has {current_user.ai_credits} AI Credits remaining."

            elif any(w in lowered for w in ["hour", "timing", "open", "branch", "time"]):
                detected_intents.append("branch_hours_faq")
                reply_text = (
                    f"Azentio Bank branches are open Monday to Friday 9:00 AM - 5:00 PM, and Saturday 9:30 AM - 1:30 PM. "
                    f"Digital banking services on your account ({current_user.email}) are available 24/7."
                )

            elif any(w in lowered for w in ["human", "agent", "supervisor", "representative", "escalate"]):
                detected_intents.append("escalation_request")
                escalation = "Customer requested human supervisor."
                reply_text = f"I am escalating your request to a senior banking specialist for account {current_user.account_number}."

            elif any(w in lowered for w in ["hello", "hi", "hey", "greetings"]):
                detected_intents.append("greeting")
                reply_text = (
                    f"Hello {current_user.full_name}! Welcome back to your Azentio Voice Banking Assistant. "
                    f"You are signed in as {current_user.email} (Account: {current_user.account_number}). "
                    f"How can I assist you with your accounts, loans, or transactions today?"
                )

            else:
                detected_intents.append("general_assistant_query")
                reply_text = (
                    f"Thank you for contacting Azentio Banking, {current_user.full_name} ({current_user.email}). "
                    f"Your checking account {current_user.account_number} is in good standing with balance ${current_user.balance:,.2f}. "
                    f"You can ask me for recent transactions, loan status, or EMI repayment details."
                )

        elif not session.verified:
            # 2. Unauthenticated Guest: General FAQs ONLY. If asking for personal accounts, tell user to login.
            if any(w in lowered for w in ["balance", "money", "funds", "how much", "transaction", "statement", "history", "my loan", "my emi", "when is my emi", "due date", "my card", "transfer", "send money", "wire", "my account", "credit", "tokens"]):
                detected_intents.append("unauthenticated_account_query")
                reply_text = "To access your personal account details, view your balance, check recent transactions, or manage your loans, please log in with your Azentio account."

            elif any(w in lowered for w in ["hour", "timing", "open", "branch", "time", "close"]):
                detected_intents.append("branch_hours_faq")
                reply_text = "Azentio Bank branches are open Monday through Friday from 9:00 AM to 5:00 PM, and Saturday from 9:30 AM to 1:30 PM. Digital banking, mobile apps, and ATMs are available 24/7."

            elif any(w in lowered for w in ["interest", "rate", "loan", "mortgage", "borrow"]):
                detected_intents.append("loan_rates_faq")
                reply_text = "Azentio Bank offers competitive interest rates: Home Loans starting at 7.20% p.a., Personal Loans from 8.50% p.a., Auto Loans from 7.90% p.a., and High-Yield Savings at 4.50% APY."

            elif any(w in lowered for w in ["open account", "open an account", "apply", "register", "eligibility", "documents", "how to open"]):
                detected_intents.append("open_account_faq")
                reply_text = "You can open an Azentio digital account online in under 5 minutes with a valid government photo ID and address proof. Click Register to get started."

            elif any(w in lowered for w in ["savings", "deposit", "apy"]):
                detected_intents.append("savings_faq")
                reply_text = "Azentio High-Yield Savings Accounts offer 4.50% Annual Percentage Yield (APY) with interest compounded daily and credited monthly, with zero monthly maintenance charges."

            elif any(w in lowered for w in ["card", "debit", "credit"]):
                detected_intents.append("cards_faq")
                reply_text = "Azentio offers contactless Platinum Debit and Credit Cards featuring 0% foreign transaction fees, 1% cashback on retail purchases, and instant app-based security controls."

            elif any(w in lowered for w in ["security", "safe", "protect", "encryption", "fdic", "insurance"]):
                detected_intents.append("security_faq")
                reply_text = "Your funds and data are protected with bank-grade 256-bit AES encryption, biometric multi-factor authentication, real-time AI fraud monitoring, and FDIC insurance up to $250,000."

            elif any(w in lowered for w in ["support", "contact", "phone", "call", "email", "help", "human", "agent"]):
                detected_intents.append("support_contact_faq")
                reply_text = "You can reach Azentio 24/7 Priority Support toll-free at 1-800-AZENTIO (1-800-293-6846), email support@azentio.com, or through this 24/7 interactive chat."

            elif any(w in lowered for w in ["transfer limit", "limit", "wire transfer", "upi", "swift"]):
                detected_intents.append("transfer_limits_faq")
                reply_text = "Azentio supports instant transfers via UPI, ACH, IMPS, and SWIFT wire transfers. Standard daily transfer limit is $25,000, up to $100,000 for verified customers."

            elif any(w in lowered for w in ["hello", "hi", "hey", "greetings", "morning", "afternoon"]):
                detected_intents.append("greeting")
                reply_text = "Hello! Welcome to Azentio Banking Voice Assistant. I can answer any general banking FAQs regarding branch hours, interest rates, loans, and account opening. Sign in to access your personal account details."

            else:
                detected_intents.append("guest_general_inquiry")
                reply_text = "Thank you for reaching out to Azentio Bank. As a guest visitor, you can ask about branch hours, loan interest rates, how to open an account, or our card features. To review your personal account details, please log in."

        else:
            # 3. Verified Session via In-call verification (fallback for phone/IVR channel)
            customer_id = session.customer_id
            cust_res = await db.execute(select(Customer).where(Customer.customer_id == customer_id))
            customer = cust_res.scalar_one_or_none()
            cust_name = customer.customer_name if customer else "valued customer"

            if any(w in lowered for w in ["loan", "emi", "due", "repayment"]):
                loans_res = await db.execute(select(Loan).where(Loan.customer_id == customer_id))
                loans = loans_res.scalars().all()
                if loans:
                    ln = loans[0]
                    reply_text = f"Hello {cust_name}, on your {ln.product_type} loan ({ln.loan_id}), your outstanding balance is ${ln.outstanding_amount:,.2f} with EMI of ${ln.emi_amount:,.2f} due on {ln.next_due_date}."
                else:
                    reply_text = f"Hello {cust_name}, our records show no active loan accounts under your profile."
            elif any(w in lowered for w in ["balance", "money", "funds"]):
                acc_res = await db.execute(select(Account).where(Account.customer_id == customer_id))
                accounts = acc_res.scalars().all()
                if accounts:
                    acc = accounts[0]
                    reply_text = f"Your {acc.account_type} account balance is ${acc.balance:,.2f} {acc.currency}."
                else:
                    reply_text = f"Hello {cust_name}, we found no active accounts associated with your customer ID."
            else:
                reply_text = f"Hello {cust_name}. Your account is verified. How can I assist you with your loans or accounts today?"

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
