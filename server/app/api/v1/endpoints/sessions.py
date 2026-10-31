from typing import List, Optional
from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.integrations.ai_pipeline import process_ai_turn
from app.models.vaani_models import Customer, Session
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
from app.core.security import get_optional_current_user
from app.models.user import User

router = APIRouter()


@router.post(
    "",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create assistant voice or chat session",
)
async def api_create_session(
    payload: SessionCreate = SessionCreate(),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionOut:
    cust_id = payload.customer_id
    if current_user and not cust_id:
        cust_id = 'C1023' if current_user.email == 'customer@azentio.com' else current_user.email

    session, call = await create_session(
        db=db,
        customer_id=cust_id,
        channel=payload.channel,
    )

    if current_user:
        session.verified = True
        session.current_state = 'VERIFIED'
        await db.commit()
        await db.refresh(session)
        greeting = (
            f"Hello {current_user.full_name}! Welcome back to your Azentio Voice Banking Assistant. "
            f"You are signed in as {current_user.email} (Account: {current_user.account_number}). "
            f"How can I assist you with your accounts, loans, or transactions today?"
        )
    else:
        greeting = (
            "Hello! Welcome to Azentio Banking Voice Assistant. "
            "I can answer any general banking FAQs regarding our services, branch hours, loan products, and interest rates. "
            "To access personal account details or check your balance, please sign in."
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
        greeting=greeting,
    )


@router.get(
    "",
    response_model=List[SessionOut],
    summary="List active sessions",
)
async def api_list_sessions(
    db: AsyncSession = Depends(get_db),
) -> List[SessionOut]:
    result = await db.execute(select(Session).order_by(Session.created_at.desc()).limit(50))
    sessions = result.scalars().all()
    return [
        SessionOut(
            session_id=s.session_id,
            call_id=s.session_id,
            customer_id=s.customer_id,
            current_state=s.current_state,
            verified=s.verified,
            failed_verification_attempts=s.failed_verification_attempts,
            locked=s.locked,
            created_at=s.created_at,
        )
        for s in sessions
    ]


@router.get(
    "/{session_id}",
    summary="Session details and status",
)
async def api_get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    session = await get_session(db, session_id)
    call = await get_session_call(db, session_id)
    return {
        "session_id": session.session_id,
        "call_id": call.call_id if call else None,
        "customer_id": session.customer_id,
        "current_state": session.current_state,
        "verified": session.verified,
        "failed_verification_attempts": session.failed_verification_attempts,
        "locked": session.locked,
        "created_at": session.created_at,
    }


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
    request: Request,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> TurnResponse:
    session = await get_session(db, session_id)
    call = await get_session_call(db, session_id)
    if not call:
        from app.core.exceptions import ResourceNotFoundException
        raise ResourceNotFoundException(f"No active call associated with session '{session_id}'.")

    text = ""
    input_type = "voice_transcript"

    if request.headers.get("content-type", "").startswith("multipart/form-data"):
        form = await request.form()
        text = str(form.get("text") or form.get("transcript") or "")
        input_type = "voice_audio"
        if not text:
            text = "Voice message received"
    else:
        body = await request.json()
        text = body.get("text", "")
        input_type = body.get("input_type", "voice_transcript")

    result = await process_ai_turn(
        db=db,
        session=session,
        call=call,
        text=text,
        input_type=input_type,
        current_user=current_user,
    )
    return TurnResponse(**result)


@router.post(
    "/{session_id}/turn/audio",
    response_model=TurnResponse,
    summary="Process a spoken turn (audio file: webm/ogg/mp3/wav) with the AI pipeline",
)
async def api_process_audio_turn(
    session_id: str,
    audio: UploadFile = File(..., description="Recorded customer speech"),
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
        audio=(audio.filename or "turn.webm", await audio.read(), audio.content_type or "application/octet-stream"),
    )
    return TurnResponse(**result)


@router.post(
    "/{session_id}/escalate",
    response_model=EscalateResponse,
    summary="Escalate session to human representative",
)
async def api_escalate_session(
    session_id: str,
    payload: Optional[EscalateRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> EscalateResponse:
    reason = payload.reason if payload else "Customer requested human supervisor"
    category = (payload.category if payload and payload.category else "complaint")
    priority = (payload.priority if payload and payload.priority else "HIGH")

    session, call, escalation, ticket_id = await escalate_session(
        db=db,
        session_id=session_id,
        reason=reason,
        category=category,
        priority=priority,
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
    payload: Optional[EndSessionRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> EndSessionResponse:
    reason = payload.reason if payload and payload.reason else "Customer ended interaction"
    session, call = await end_session(
        db=db,
        session_id=session_id,
        reason=reason,
    )
    return EndSessionResponse(
        session_id=session.session_id,
        call_id=call.call_id if call else "CALL-N/A",
        status=session.current_state,
        message="Session terminated successfully.",
    )

