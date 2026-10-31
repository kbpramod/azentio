import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ResourceNotFoundException, VaaniException
from sqlalchemy import text
from app.models.vaani_models import Call, Customer, ConversationTurn, Escalation, EscalationTicket, Session, Ticket
from app.services.audit_service import record_audit_event


def utcnow():
    return datetime.now(timezone.utc)


async def create_session(
    db: AsyncSession,
    customer_id: Optional[str] = None,
    channel: str = "voice",
) -> Tuple[Session, Call]:
    session_id = f"SES-{uuid.uuid4().hex[:8]}"
    call_id = f"CALL-{uuid.uuid4().hex[:8]}"

    # Verify customer exists if customer_id passed upfront
    if customer_id:
        result = await db.execute(select(Customer).where(Customer.customer_id == customer_id))
        if not result.scalar_one_or_none():
            # If customer does not exist in DB, treat as unassociated session
            customer_id = None

    session = Session(
        session_id=session_id,
        customer_id=customer_id,
        channel=channel,
        current_state="UNVERIFIED",
        verified=False,
        failed_verification_attempts=0,
        locked=False,
    )
    db.add(session)
    await db.flush()

    call = Call(
        call_id=call_id,
        session_id=session_id,
        customer_id=customer_id,
        outcome="IN_PROGRESS",
        escalation_status="NONE",
    )
    db.add(call)
    await db.flush()

    await record_audit_event(
        db=db,
        event_type="SESSION_CREATED",
        event_status="SUCCESS",
        session_id=session_id,
        call_id=call_id,
        metadata={"channel": channel, "customer_id": customer_id},
    )

    await db.commit()
    await db.refresh(session)
    await db.refresh(call)
    return session, call


async def get_session(db: AsyncSession, session_id: str) -> Session:
    result = await db.execute(select(Session).where(Session.session_id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise ResourceNotFoundException(f"Session '{session_id}' not found.")
    return session


async def get_session_call(db: AsyncSession, session_id: str) -> Optional[Call]:
    result = await db.execute(
        select(Call).where(Call.session_id == session_id).order_by(Call.started_at.desc())
    )
    return result.scalars().first()


async def end_session(
    db: AsyncSession,
    session_id: str,
    reason: Optional[str] = None,
    current_user: Optional[Any] = None,
) -> Tuple[Session, Optional[Call], Optional[Ticket], Optional[EscalationTicket]]:
    # 1. Ensure table escalation_tickets exists in database
    try:
        from app.db.session import Base
        bind_engine = db.bind
        if bind_engine:
            async with bind_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
    except Exception:
        pass

    session = await get_session(db, session_id)
    call = await get_session_call(db, session_id)

    session.current_state = "ENDED"
    session.ended_at = utcnow()

    if call and not call.ended_at:
        call.ended_at = utcnow()
        if call.outcome == "IN_PROGRESS":
            call.outcome = "RESOLVED"

    # 2. Retrieve all conversation turns for this session
    turns_res = await db.execute(
        select(ConversationTurn)
        .where(ConversationTurn.session_id == session_id)
        .order_by(ConversationTurn.turn_number.asc())
    )
    turns = turns_res.scalars().all()

    user_queries = []
    ai_replies = []
    transcript_lines = []
    has_escalation_intent = False
    has_failed_verification = False
    unhandled_reason = None

    for t in turns:
        u_txt = (t.transcript_text or "").strip()
        bot_txt = (t.reply_text or "").strip()
        if u_txt:
            user_queries.append(u_txt)
            transcript_lines.append(f"Turn {t.turn_number} User: {u_txt}")
        if bot_txt:
            ai_replies.append(bot_txt)
            transcript_lines.append(f"Turn {t.turn_number} Azentio Voice: {bot_txt}")

        intents = t.detected_intents or []
        if any(i in ["escalation_request", "unhandled", "unresolved"] for i in intents):
            has_escalation_intent = True
            unhandled_reason = unhandled_reason or "Customer requested human supervisor or inquiry could not be resolved by AI."
        if "verification_failure" in intents or "unauthenticated_account_query" in intents:
            has_failed_verification = True
            unhandled_reason = unhandled_reason or "Customer verification failed or unauthenticated account inquiry."

        u_lowered = u_txt.lower()
        if any(w in u_lowered for w in ["human", "supervisor", "representative", "real person", "agent", "escalate", "not helping"]):
            has_escalation_intent = True
            unhandled_reason = unhandled_reason or f"Customer requested human representative: '{u_txt}'"

    # 3. Determine if AI was unable to handle the session
    session_was_escalated = (session.current_state in ["ESCALATED", "LOCKED"]) or (call and call.escalation_status == "ESCALATED")
    reason_lowered = (reason or "").lower()
    reason_indicates_escalation = any(w in reason_lowered for w in ["escalat", "human", "supervisor", "agent", "not handle", "unable", "fail", "unresolved", "error"])

    not_handled = (
        session_was_escalated
        or has_escalation_intent
        or reason_indicates_escalation
        or (session.locked is True)
        or (session.failed_verification_attempts > 0 and not session.verified)
    )

    if not_handled and not unhandled_reason:
        unhandled_reason = reason if reason_indicates_escalation else "AI voice assistant was unable to resolve customer inquiry."

    # 4. Identity resolution
    cust_name = None
    cust_email = None
    resolved_cust_id = session.customer_id

    if current_user:
        cust_name = getattr(current_user, "full_name", None)
        cust_email = getattr(current_user, "email", None)
        if not resolved_cust_id:
            resolved_cust_id = "C1023" if getattr(current_user, "email", "") == "customer@azentio.com" else getattr(current_user, "email", None)

    if resolved_cust_id and not cust_name:
        c_res = await db.execute(select(Customer).where(Customer.customer_id == resolved_cust_id))
        cust_obj = c_res.scalar_one_or_none()
        if cust_obj:
            cust_name = cust_obj.customer_name
            cust_email = cust_obj.email

    if not cust_name:
        cust_name = "Guest Visitor" if not session.verified else "Customer"

    # 5. Add or update Ticket in tickets table
    tck_res = await db.execute(select(Ticket).where(Ticket.session_id == session_id))
    existing_ticket = tck_res.scalars().first()

    summary_queries = ("; ".join(user_queries)[:200]) if user_queries else (reason or "Session completed")
    ticket_summary = f"{'[ESCALATED] ' if not_handled else '[CLOSED] '}Session {session_id}: {summary_queries}"

    # Ensure valid customer_id for foreign key
    valid_cid = resolved_cust_id
    if valid_cid:
        c_check = await db.execute(select(Customer).where(Customer.customer_id == valid_cid))
        if not c_check.scalar_one_or_none():
            valid_cid = "C1023"
    else:
        valid_cid = "C1023"

    if existing_ticket:
        ticket = existing_ticket
        ticket.summary = ticket_summary
        if not_handled:
            ticket.escalated = True
            ticket.escalation_reason = unhandled_reason
            ticket.priority = "HIGH"
            ticket.status = "OPEN"
        else:
            ticket.status = "CLOSED"
    else:
        ticket = Ticket(
            ticket_id=f"TCK-{uuid.uuid4().hex[:8].upper()}",
            customer_id=valid_cid,
            session_id=session_id,
            call_id=call.call_id if call else None,
            ticket_type="escalation" if not_handled else "voice_session_summary",
            category="Customer Escalation" if not_handled else "Voice Assistance",
            summary=ticket_summary,
            priority="HIGH" if not_handled else "NORMAL",
            status="OPEN" if not_handled else "CLOSED",
            escalated=not_handled,
            escalation_reason=unhandled_reason if not_handled else None,
            idempotency_key=f"SESSION-END-{session_id}",
        )
        db.add(ticket)
        await db.flush()

    # 6. If AI was NOT able to handle, add record into escalation_tickets table
    esc_ticket = None
    if not_handled:
        esc_check = await db.execute(select(EscalationTicket).where(EscalationTicket.session_id == session_id))
        existing_esc_tck = esc_check.scalars().first()
        if existing_esc_tck:
            esc_ticket = existing_esc_tck
        else:
            esc_ticket = EscalationTicket(
                escalation_ticket_id=f"ESC-TCK-{uuid.uuid4().hex[:8].upper()}",
                ticket_id=ticket.ticket_id,
                session_id=session_id,
                call_id=call.call_id if call else None,
                customer_id=resolved_cust_id or "GUEST",
                customer_name=cust_name,
                customer_email=cust_email,
                reason=unhandled_reason,
                query_summary="; ".join(user_queries)[:500] if user_queries else (reason or "AI voice session unhandled"),
                transcript="\n".join(transcript_lines)[:4000] if transcript_lines else (reason or "No transcript recorded"),
                ai_turns_count=len(turns),
                status="PENDING_HUMAN_REVIEW",
                priority="HIGH",
                created_at=utcnow(),
            )
            db.add(esc_ticket)

        if call:
            call.outcome = "ESCALATED"
            call.escalation_status = "ESCALATED"
        session.current_state = "ESCALATED"

    await record_audit_event(
        db=db,
        event_type="SESSION_ENDED",
        event_status="SUCCESS",
        session_id=session_id,
        call_id=call.call_id if call else None,
        metadata={
            "reason": reason or "Interaction ended",
            "ticket_id": ticket.ticket_id if ticket else None,
            "escalated": not_handled,
            "escalation_ticket_id": esc_ticket.escalation_ticket_id if esc_ticket else None,
        },
    )

    await db.commit()
    await db.refresh(session)
    if call:
        await db.refresh(call)
    if ticket:
        await db.refresh(ticket)
    if esc_ticket:
        await db.refresh(esc_ticket)

    return session, call, ticket, esc_ticket



async def escalate_session(
    db: AsyncSession,
    session_id: str,
    reason: str,
    category: str = "complaint",
    priority: str = "HIGH",
) -> Tuple[Session, Call, Escalation, Optional[str]]:
    session = await get_session(db, session_id)
    call = await get_session_call(db, session_id)
    if not call:
        raise ResourceNotFoundException(f"No active call found for session '{session_id}'.")

    # Check for existing escalation to avoid duplicate records on retry
    esc_result = await db.execute(
        select(Escalation).where(Escalation.session_id == session_id)
    )
    existing_esc = esc_result.scalars().first()
    if existing_esc:
        return session, call, existing_esc, existing_esc.ticket_id

    # Create ticket for the escalation
    ticket_id = f"SR-{uuid.uuid4().hex[:6].upper()}"
    ticket = Ticket(
        ticket_id=ticket_id,
        customer_id=session.customer_id or "ANONYMOUS",
        session_id=session_id,
        call_id=call.call_id,
        ticket_type="complaint" if category == "complaint" else "service_request",
        category=category,
        summary=f"Escalation: {reason}",
        priority=priority,
        status="OPEN",
        idempotency_key=f"ESC-{session_id}-{call.call_id}",
    )
    db.add(ticket)
    await db.flush()

    escalation_id = f"ESC-{uuid.uuid4().hex[:6].upper()}"
    escalation = Escalation(
        escalation_id=escalation_id,
        call_id=call.call_id,
        session_id=session_id,
        customer_id=session.customer_id,
        reason=reason,
        ticket_id=ticket_id,
        status="PENDING_AGENT",
    )
    db.add(escalation)

    call.escalation_status = "ESCALATED"
    call.outcome = "ESCALATED"
    session.current_state = "ESCALATED"

    await record_audit_event(
        db=db,
        event_type="ESCALATION_CREATED",
        event_status="SUCCESS",
        session_id=session_id,
        call_id=call.call_id,
        metadata={"reason": reason, "ticket_id": ticket_id, "escalation_id": escalation_id},
    )

    await db.commit()
    await db.refresh(session)
    await db.refresh(call)
    await db.refresh(escalation)
    return session, call, escalation, ticket_id

