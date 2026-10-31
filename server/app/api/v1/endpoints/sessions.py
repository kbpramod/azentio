from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.integrations.ai_pipeline import process_ai_turn
from app.schemas.vaani_schemas import (
    EndSessionRequest,
    EndSessionResponse,
    EscalateRequest,
    EscalateResponse,
    SessionCreate,
    SessionOut,
    TurnRequest,
    TurnResponse,
    VerifyRequest,
    VerifyResponse,
)
from app.services.session_service import (
    create_session,
    end_session,
    escalate_session,
    get_session,
    get_session_call,
)
from app.services.verification_service import verify_customer_identity

router = APIRouter()


@router.post(
    "",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create assistant voice or chat session",
)
async def api_create_session(
    payload: SessionCreate = SessionCreate(),
    db: AsyncSession = Depends(get_db),
) -> SessionOut:
    session, call = await create_session(
        db=db,
        customer_id=payload.customer_id,
        channel=payload.channel,
    )
    return SessionOut(
        session_id=session.session_id,
        call_id=call.call_id,
        customer_id=session.customer_id,
        current_state=session.current_state,
        verified=session.verified,
        failed_verification_attempts=session.failed_verification_attempts,
        locked=session.locked,
        created_at=session.created_at,
    )


@router.post(
    "/{session_id}/verify",
    response_model=VerifyResponse,
    summary="Verify customer identity via Date of Birth",
)
async def api_verify_customer(
    session_id: str,
    payload: VerifyRequest,
    db: AsyncSession = Depends(get_db),
) -> VerifyResponse:
    session = await verify_customer_identity(
        db=db,
        session_id=session_id,
        customer_id=payload.customer_id,
        dob=payload.dob,
    )
    # Fetch customer name for friendly return message
    from sqlalchemy import select
    from app.models.vaani_models import Customer
    c_res = await db.execute(select(Customer).where(Customer.customer_id == payload.customer_id))
    cust = c_res.scalar_one_or_none()
    cust_name = cust.customer_name if cust else payload.customer_id

    return VerifyResponse(
        session_id=session.session_id,
        verified=session.verified,
        customer_id=session.customer_id,
        customer_name=cust_name,
        current_state=session.current_state,
        message="Customer identity verified successfully.",
    )


@router.post(
    "/{session_id}/turn",
    response_model=TurnResponse,
    summary="Process conversation turn with AI pipeline",
)
async def api_process_turn(
    session_id: str,
    payload: TurnRequest,
    db: AsyncSession = Depends(get_db),
) -> TurnResponse:
    session = await get_session(db, session_id)
    call = await get_session_call(db, session_id)
    if not call:
        from app.core.exceptions import ResourceNotFoundException
        raise ResourceNotFoundException(f"No active call associated with session '{session_id}'.")

    result = await process_ai_turn(
        db=db,
        session=session,
        call=call,
        text=payload.text,
        input_type=payload.input_type,
    )
    return TurnResponse(**result)


@router.post(
    "/{session_id}/escalate",
    response_model=EscalateResponse,
    summary="Escalate session to human representative",
)
async def api_escalate_session(
    session_id: str,
    payload: EscalateRequest,
    db: AsyncSession = Depends(get_db),
) -> EscalateResponse:
    session, call, escalation, ticket_id = await escalate_session(
        db=db,
        session_id=session_id,
        reason=payload.reason,
        category=payload.category or "complaint",
        priority=payload.priority or "HIGH",
    )
    return EscalateResponse(
        session_id=session.session_id,
        call_id=call.call_id,
        escalated=True,
        escalation_id=escalation.escalation_id,
        ticket_id=ticket_id,
        message="Call successfully transferred to human agent queue.",
    )


@router.post(
    "/{session_id}/end",
    response_model=EndSessionResponse,
    summary="End session and finalize call record",
)
async def api_end_session(
    session_id: str,
    payload: EndSessionRequest = EndSessionRequest(),
    db: AsyncSession = Depends(get_db),
) -> EndSessionResponse:
    session, call = await end_session(
        db=db,
        session_id=session_id,
        reason=payload.reason,
    )
    return EndSessionResponse(
        session_id=session.session_id,
        call_id=call.call_id if call else "CALL-N/A",
        status=session.current_state,
        message="Session terminated successfully.",
    )

