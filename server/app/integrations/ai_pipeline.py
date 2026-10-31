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
    Escalation,
    Loan,
    LoanApplication,
    Session,
)
from app.services.audit_service import record_audit_event


async def _rule_based_turn(
    db: AsyncSession,
    session: Session,
    call: Call,
    text: str,
    input_type: str = "voice_transcript",
) -> Dict[str, Any]:
    """Keyword fallback used when the AI service (Member 2) is not reachable."""
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


# ---------------------------------------------------------------------------
# Member 2 AI orchestration service (azentio/ai, default http://127.0.0.1:8001).
# It runs as a separate process because both projects use a package named `app`.
# ---------------------------------------------------------------------------
import httpx  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from app.core.config import settings  # noqa: E402

AI_TIMEOUT = httpx.Timeout(60.0, connect=3.0)  # speech-to-text on CPU takes a few seconds
_AI_SESSIONS: Dict[str, str] = {}  # server session_id -> AI session_id (in memory)
_TURN_NO: Dict[str, int] = {}      # call_id -> last turn number (saves a COUNT query per turn)


def _audit(db: AsyncSession, event_type: str, session_id: str, call_id: str, metadata: Dict[str, Any]) -> None:
    """Same row as record_audit_event, but saved with the turn's commit instead of its own flush
    (each extra round trip to the US-region database costs ~0.3-0.5 s)."""
    from app.models.vaani_models import AuditEvent
    from app.services.audit_service import sanitize_metadata
    db.add(AuditEvent(session_id=session_id, call_id=call_id, event_type=event_type,
                      event_status="SUCCESS", safe_metadata=sanitize_metadata(metadata)))


class AIUnavailable(Exception):
    pass


async def _ai_request(method: str, path: str, **kwargs):
    url = f"{settings.AI_SERVICE_URL.rstrip('/')}/api/v1{path}"
    try:
        async with httpx.AsyncClient(timeout=AI_TIMEOUT) as client:
            res = await client.request(method, url, **kwargs)
    except httpx.HTTPError as exc:
        raise AIUnavailable(str(exc)) from exc
    body = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
    return res.status_code, body


async def _ai_session_id(session: Session, fresh: bool = False) -> str:
    if not fresh and session.session_id in _AI_SESSIONS:
        return _AI_SESSIONS[session.session_id]
    # if the server already verified the customer (e.g. /verify form), the AI won't ask again
    body = {"customer_id": session.customer_id, "pre_verified": True} if session.verified else {}
    code, data = await _ai_request("POST", "/sessions", json=body)
    if code >= 400:
        raise AIUnavailable(f"AI session create failed: {code}")
    _AI_SESSIONS[session.session_id] = data["session_id"]
    return data["session_id"]


async def _ai_turn(session: Session, text: str, audio: Optional[tuple]) -> Dict[str, Any]:
    for fresh in (False, True):  # retry once with a new AI session if the AI service restarted
        ai_sid = await _ai_session_id(session, fresh=fresh)
        if audio is not None:
            code, data = await _ai_request("POST", f"/sessions/{ai_sid}/turn", files={"audio": audio})
        else:
            code, data = await _ai_request("POST", f"/sessions/{ai_sid}/turn", json={"text": text})
        if code == 404 and not fresh:
            continue
        if code == 422 and audio is not None:
            raise HTTPException(422, detail=data.get("detail", data))  # unreadable audio
        if code >= 400:
            raise AIUnavailable(f"AI turn failed: {code}")
        return data
    raise AIUnavailable("AI session lost")


async def process_ai_turn(
    db: AsyncSession,
    session: Session,
    call: Call,
    text: str = "",
    input_type: str = "voice_transcript",
    audio: Optional[tuple] = None,
) -> Dict[str, Any]:
    """Entry point for POST /sessions/{id}/turn and /turn/audio.

    Sends the turn to Member 2's AI service; falls back to the keyword engine for text if it is down.
    `audio` is (filename, bytes, content_type).
    """
    try:
        ai = await _ai_turn(session, text, audio)
    except AIUnavailable:
        if audio is not None:
            raise HTTPException(503, detail={"error": {
                "code": "AI_UNAVAILABLE", "retryable": True,
                "message": "Voice needs the AI service on port 8001. Type your question instead."}})
        return await _rule_based_turn(db, session, call, text, input_type)

    # keep the server session in step with verification done inside the conversation
    if ai.get("verified") and not session.verified and ai.get("customer_id"):
        session.verified = True
        session.customer_id = ai["customer_id"]
        session.current_state = "VERIFIED"
        call.customer_id = ai["customer_id"]
        _audit(db, "VERIFICATION", session.session_id, call.call_id,
               {"via": "voice_agent", "customer_id": ai["customer_id"]})
    escalation = ai.get("escalation")
    if escalation and session.current_state != "ESCALATED":
        # same record the manual /escalate endpoint creates, so the ops escalation queue shows it;
        # reuse the AI's ticket (e.g. the fraud complaint) instead of opening a second one
        existing = (await db.execute(
            select(Escalation).where(Escalation.session_id == session.session_id)
        )).scalars().first()
        if existing is None:
            escalation_id = f"ESC-{uuid.uuid4().hex[:6].upper()}"
            summary = escalation.get("summary") or ""
            db.add(Escalation(
                escalation_id=escalation_id, call_id=call.call_id, session_id=session.session_id,
                customer_id=session.customer_id,
                reason=f"{escalation.get('reason')} ({escalation.get('priority', 'NORMAL')}): {summary}"[:1000],
                ticket_id=escalation.get("ticket_id"), status="PENDING_AGENT",
            ))
            _audit(db, "ESCALATION_CREATED", session.session_id, call.call_id, {"reason": escalation.get("reason"), "priority": escalation.get("priority"),
                                               "ticket_id": escalation.get("ticket_id"),
                                               "escalation_id": escalation_id, "via": "voice_agent"})
        call.escalation_status = "ESCALATED"
        call.outcome = "ESCALATED"
        session.current_state = "ESCALATED"

    if call.call_id not in _TURN_NO:  # first turn seen by this process: count once
        count_res = await db.execute(
            select(func.count(ConversationTurn.turn_id)).where(ConversationTurn.call_id == call.call_id)
        )
        _TURN_NO[call.call_id] = count_res.scalar() or 0
    _TURN_NO[call.call_id] += 1
    turn_count = _TURN_NO[call.call_id]
    turn_id = f"TURN-{uuid.uuid4().hex[:6].upper()}"
    intents = [i["name"] for i in ai.get("intents", [])]
    transcript = ai.get("transcript") or text

    db.add(ConversationTurn(
        turn_id=turn_id, call_id=call.call_id, session_id=session.session_id, turn_number=turn_count,
        input_type="voice_audio" if audio is not None else input_type, transcript=transcript,
        detected_intents=intents, reply_text=ai["reply_text"], processing_status="COMPLETED",
    ))
    _audit(db, "TURN_PROCESSED", session.session_id, call.call_id, {"turn_id": turn_id, "turn_number": turn_count, "intents": intents,
                                       "engine": "ai_service", "latency_ms": ai.get("latency_ms")})
    await db.commit()

    return {
        "turn_id": turn_id,
        "session_id": session.session_id,
        "call_id": call.call_id,
        "turn_number": turn_count,
        "reply_text": ai["reply_text"],
        "detected_intents": intents,
        "state": session.current_state,
        "verified": session.verified,
        "tickets": [t["ticket_id"] for t in ai.get("tickets", [])],
        "escalation": escalation.get("reason") if escalation else None,
        # extra detail for the UI
        "transcript": transcript,
        "stt_confidence": ai.get("stt_confidence"),
        "reply_audio_url": ai.get("reply_audio_url"),
        "sources": ai.get("sources", []),
        "ticket_details": ai.get("tickets", []),
        "escalation_detail": escalation,
        "agent_state": ai.get("state"),
        "engine": "ai_service",
    }
