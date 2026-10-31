import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ResourceNotFoundException, VaaniException
from app.models.vaani_models import Call, Customer, Escalation, Session, Ticket
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
) -> Tuple[Session, Optional[Call]]:
    session = await get_session(db, session_id)
    if session.current_state == "ENDED":
        call = await get_session_call(db, session_id)
        return session, call

    session.current_state = "ENDED"
    session.ended_at = utcnow()

    call = await get_session_call(db, session_id)
    if call and not call.ended_at:
        call.ended_at = utcnow()
        if call.outcome == "IN_PROGRESS":
            call.outcome = "RESOLVED"

    await record_audit_event(
        db=db,
        event_type="SESSION_ENDED",
        event_status="SUCCESS",
        session_id=session_id,
        call_id=call.call_id if call else None,
        metadata={"reason": reason or "Interaction ended normally"},
    )

    await db.commit()
    await db.refresh(session)
    if call:
        await db.refresh(call)
    return session, call


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

