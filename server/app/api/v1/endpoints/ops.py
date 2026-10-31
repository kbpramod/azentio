from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.vaani_schemas import (
    CallDetailOut,
    CallListResponse,
    CallSummaryOut,
    EscalationListResponse,
    EscalationOut,
    TicketListResponse,
    TicketOut,
)
from app.services.ops_service import get_ops_call_detail, list_ops_calls, list_ops_escalations
from app.services.ticket_service import list_csm_tickets

router = APIRouter()


@router.get(
    "/calls",
    response_model=CallListResponse,
    summary="Operations: List customer service call history",
)
async def api_ops_list_calls(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    customer_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> CallListResponse:
    total, calls = await list_ops_calls(
        db=db, limit=limit, offset=offset, customer_id=customer_id
    )
    return CallListResponse(
        total=total,
        calls=[CallSummaryOut.model_validate(c) for c in calls],
    )


@router.get(
    "/calls/{call_id}",
    response_model=CallDetailOut,
    summary="Operations: Retrieve call details, conversation turns, and audit trace",
)
async def api_ops_call_detail(
    call_id: str,
    db: AsyncSession = Depends(get_db),
) -> CallDetailOut:
    detail = await get_ops_call_detail(db=db, call_id=call_id)
    return CallDetailOut(**detail)


@router.get(
    "/tickets",
    response_model=TicketListResponse,
    summary="Operations: List and filter customer service tickets",
)
async def api_ops_list_tickets(
    status: Optional[str] = Query(None, description="OPEN, IN_PROGRESS, RESOLVED, CLOSED"),
    priority: Optional[str] = Query(None, description="LOW, NORMAL, HIGH, URGENT"),
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> TicketListResponse:
    tickets = await list_csm_tickets(
        db=db, status=status, priority=priority, category=category, limit=limit
    )
    return TicketListResponse(
        total=len(tickets),
        tickets=[TicketOut.model_validate(t) for t in tickets],
    )


@router.get(
    "/escalations",
    response_model=EscalationListResponse,
    summary="Operations: List active escalations requiring human supervisor attention",
)
async def api_ops_list_escalations(
    status: Optional[str] = Query(None, description="PENDING_AGENT, RESOLVED"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> EscalationListResponse:
    total, escalations = await list_ops_escalations(db=db, status=status, limit=limit)
    return EscalationListResponse(
        total=total,
        escalations=[EscalationOut.model_validate(e) for e in escalations],
    )

