from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ResourceNotFoundException
from app.models.vaani_models import AuditEvent, Call, ConversationTurn, Escalation, Ticket


async def list_ops_calls(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
    customer_id: Optional[str] = None,
) -> Tuple[int, List[Call]]:
    count_stmt = select(func.count(Call.call_id))
    if customer_id:
        count_stmt = count_stmt.where(Call.customer_id == customer_id)
    total_count = (await db.execute(count_stmt)).scalar() or 0

    stmt = select(Call).order_by(Call.started_at.desc()).limit(limit).offset(offset)
    if customer_id:
        stmt = stmt.where(Call.customer_id == customer_id)

    result = await db.execute(stmt)
    calls = result.scalars().all()
    return total_count, list(calls)


async def get_ops_call_detail(db: AsyncSession, call_id: str) -> dict:
    call_res = await db.execute(select(Call).where(Call.call_id == call_id))
    call = call_res.scalar_one_or_none()
    if not call:
        raise ResourceNotFoundException(f"Call record '{call_id}' not found.")

    # Turns
    turn_res = await db.execute(
        select(ConversationTurn)
        .where(ConversationTurn.call_id == call_id)
        .order_by(ConversationTurn.turn_number.asc())
    )
    turns = turn_res.scalars().all()

    # Associated tickets
    ticket_res = await db.execute(
        select(Ticket.ticket_id).where(Ticket.call_id == call_id)
    )
    ticket_ids = ticket_res.scalars().all()

    # Audit events
    audit_res = await db.execute(
        select(AuditEvent)
        .where((AuditEvent.call_id == call_id) | (AuditEvent.session_id == call.session_id))
        .order_by(AuditEvent.created_at.asc())
    )
    audit_events = audit_res.scalars().all()

    return {
        "call_id": call.call_id,
        "session_id": call.session_id,
        "customer_id": call.customer_id,
        "started_at": call.started_at,
        "ended_at": call.ended_at,
        "outcome": call.outcome,
        "escalation_status": call.escalation_status,
        "turns": turns,
        "tickets": list(ticket_ids),
        "audit_events": audit_events,
    }


async def list_ops_escalations(
    db: AsyncSession,
    status: Optional[str] = None,
    limit: int = 50,
) -> Tuple[int, List[Escalation]]:
    count_stmt = select(func.count(Escalation.escalation_id))
    if status:
        count_stmt = count_stmt.where(Escalation.status == status)
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = select(Escalation).order_by(Escalation.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(Escalation.status == status)

    res = await db.execute(stmt)
    escalations = res.scalars().all()
    return total, list(escalations)

