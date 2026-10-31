from typing import Optional
from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.vaani_schemas import TicketCreateRequest, TicketOut
from app.services.ticket_service import create_csm_ticket, get_csm_ticket

router = APIRouter()


@router.post(
    "/tickets",
    response_model=TicketOut,
    status_code=status.HTTP_201_CREATED,
    summary="Mock CSM: Create service ticket with idempotency protection",
)
async def api_create_ticket(
    payload: TicketCreateRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    session_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> TicketOut:
    active_sid = x_session_id or session_id
    ticket = await create_csm_ticket(db=db, payload=payload, session_id=active_sid)
    return TicketOut.model_validate(ticket)


@router.get(
    "/tickets/{ticket_id}",
    response_model=TicketOut,
    summary="Mock CSM: Retrieve ticket by identifier",
)
async def api_get_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
) -> TicketOut:
    ticket = await get_csm_ticket(db=db, ticket_id=ticket_id)
    return TicketOut.model_validate(ticket)

