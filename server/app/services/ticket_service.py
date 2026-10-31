import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ResourceNotFoundException, VaaniException
from app.models.vaani_models import Ticket
from app.schemas.vaani_schemas import TicketCreateRequest
from app.services.audit_service import record_audit_event
from app.services.session_service import get_session


async def create_csm_ticket(
    db: AsyncSession,
    payload: TicketCreateRequest,
    session_id: Optional[str] = None,
) -> Ticket:
    # If session_id is provided, verify ownership
    if session_id:
        session = await get_session(db, session_id)
        if session.customer_id and session.customer_id != payload.customer_id:
            raise VaaniException(
                code="NOT_VERIFIED",
                message="Ticket customer ID does not match active verified session.",
                status_code=403,
                retryable=False,
            )

    # Idempotency check: if ticket with this key already exists, return existing atomically
    if payload.idempotency_key:
        existing_result = await db.execute(
            select(Ticket).where(Ticket.idempotency_key == payload.idempotency_key)
        )
        existing_ticket = existing_result.scalar_one_or_none()
        if existing_ticket:
            return existing_ticket

    ticket_id = f"SR-{uuid.uuid4().hex[:6].upper()}"
    new_ticket = Ticket(
        ticket_id=ticket_id,
        customer_id=payload.customer_id,
        session_id=session_id,
        call_id=payload.call_id,
        ticket_type=payload.type,
        category=payload.category,
        summary=payload.summary,
        priority=payload.priority,
        status="OPEN",
        idempotency_key=payload.idempotency_key,
    )
    db.add(new_ticket)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        # Handle concurrent race condition: fetch the concurrently created ticket
        existing_res = await db.execute(
            select(Ticket).where(Ticket.idempotency_key == payload.idempotency_key)
        )
        existing_ticket = existing_res.scalar_one_or_none()
        if existing_ticket:
            return existing_ticket
        raise VaaniException(
            code="CONFLICT",
            message="Database constraint violation while creating ticket.",
            status_code=409,
            retryable=False,
        )

    await record_audit_event(
        db=db,
        event_type="TICKET_CREATED",
        event_status="SUCCESS",
        session_id=session_id,
        call_id=payload.call_id,
        metadata={
            "ticket_id": ticket_id,
            "category": payload.category,
            "priority": payload.priority,
            "idempotency_key": payload.idempotency_key,
        },
    )

    await db.commit()
    await db.refresh(new_ticket)
    return new_ticket


async def get_csm_ticket(db: AsyncSession, ticket_id: str) -> Ticket:
    result = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise ResourceNotFoundException(f"Ticket '{ticket_id}' not found.")
    return ticket


async def list_csm_tickets(
    db: AsyncSession,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
) -> List[Ticket]:
    stmt = select(Ticket).order_by(Ticket.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(Ticket.status == status)
    if priority:
        stmt = stmt.where(Ticket.priority == priority)
    if category:
        stmt = stmt.where(Ticket.category == category)

    result = await db.execute(stmt)
    return list(result.scalars().all())

