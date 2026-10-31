"""Member 2 AI Orchestration Pipeline Adapter.

This module provides the stable boundary between Member 1's core FastAPI/database
subsystem and Member 2's AI orchestration engine (Speech-to-Text, Dialogue Policy,
LLM Intent Classification, Grounded Generation, and Text-to-Speech).

MEMBER 2 INTEGRATION INSTRUCTIONS:
Replace or extend the deterministic `process_ai_turn` function below with your
actual LLM/Agentic pipeline orchestrator.
Ensure that:
1. All sensitive operations respect `session.verified`.
2. Do not bypass backend authorization.
3. Return the agreed dictionary contract matching TurnResponse schema.
"""

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

    # Gating: Check whether session is verified
    if not session.verified:
        if any(w in lowered for w in ["loan", "balance", "emi", "statement", "schedule", "account", "transfer"]):
            detected_intents.append("unverified_banking_inquiry")
            reply_text = (
                "For your security, I need to verify your identity before accessing your banking records. "
                "Please provide your Customer ID and Date of Birth to proceed."
            )
        elif any(w in lowered for w in ["hello", "hi", "hey"]):
            detected_intents.append("greeting")
            reply_text = (
                "Hello! Welcome to Azentio Banking Voice Assistant. "
                "I can assist you with your loan accounts, EMI repayment schedules, and account details. "
                "Please verify your identity to access personal accounts, or ask me any general question."
            )
        elif any(w in lowered for w in ["human", "agent", "supervisor", "representative"]):
            detected_intents.append("escalation_request")
            escalation = "Customer requested human representative prior to verification."
            reply_text = "I am connecting you with a human banking officer. Please hold while I transfer your call."
        else:
            detected_intents.append("general_inquiry")
            reply_text = (
                "Thank you for contacting Azentio Banking. "
                "To review your loans or financial accounts, please complete customer verification."
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

"""Bridge to Member 2's AI orchestration service (azentio/ai, default http://127.0.0.1:8001).

The AI service runs separately because both projects use a package named `app`.
The frontend only talks to this server; these helpers forward the calls.
"""
from typing import Any, Optional

import httpx
from fastapi import HTTPException

from app.core.config import settings

TIMEOUT = httpx.Timeout(60.0, connect=5.0)  # speech-to-text on CPU can take a few seconds


async def forward(method: str, path: str, *, json: Optional[dict] = None,
                  files: Optional[dict] = None, data: Optional[dict] = None) -> Any:
    url = f"{settings.AI_SERVICE_URL.rstrip('/')}/api/v1{path}"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            res = await client.request(method, url, json=json, files=files, data=data)
    except httpx.HTTPError:
        raise HTTPException(503, detail={"error": {
            "code": "AI_UNAVAILABLE", "message": "AI service is not reachable. Start it on port 8001.",
            "retryable": True}})
    body = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
    if res.status_code >= 400:
        raise HTTPException(res.status_code, detail=body.get("detail", body))
    return body
