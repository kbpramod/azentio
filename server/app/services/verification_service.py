from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import (
    AuthMismatchException,
    LockedSessionException,
    ResourceNotFoundException,
    VaaniException,
)
from app.models.vaani_models import Call, Customer, Session
from app.services.audit_service import record_audit_event
from app.services.session_service import get_session, get_session_call


MAX_VERIFICATION_ATTEMPTS = 3


async def verify_customer_identity(
    db: AsyncSession,
    session_id: str,
    customer_id: str,
    dob: str,
) -> Session:
    # 1. Confirm session exists
    session = await get_session(db, session_id)
    call = await get_session_call(db, session_id)
    call_id = call.call_id if call else None

    # Check if session is already ended
    if session.current_state == "ENDED":
        raise VaaniException(
            code="BAD_REQUEST",
            message="Cannot verify an ended session.",
            status_code=400,
            retryable=False,
        )

    # 2. Check if already locked
    if session.locked or session.failed_verification_attempts >= MAX_VERIFICATION_ATTEMPTS:
        session.locked = True
        session.current_state = "LOCKED"
        await db.commit()
        await record_audit_event(
            db=db,
            event_type="VERIFICATION_LOCKED",
            event_status="FAILURE",
            session_id=session_id,
            call_id=call_id,
            metadata={"reason": "Attempted verification on locked session"},
        )
        raise LockedSessionException(
            "Session locked due to previous failed verification attempts. Please contact a human agent."
        )

    # 3. Confirm customer exists in synthetic database
    result = await db.execute(select(Customer).where(Customer.customer_id == customer_id))
    customer = result.scalar_one_or_none()

    if not customer:
        # Increment attempt counter for non-existent customer to prevent enumeration
        session.failed_verification_attempts += 1
        if session.failed_verification_attempts >= MAX_VERIFICATION_ATTEMPTS:
            session.locked = True
            session.current_state = "LOCKED"
            await db.commit()
            await record_audit_event(
                db=db,
                event_type="VERIFICATION_LOCKED",
                event_status="FAILURE",
                session_id=session_id,
                call_id=call_id,
                metadata={"attempts": session.failed_verification_attempts},
            )
            raise LockedSessionException(
                "Session locked due to 3 failed verification attempts. Please contact a human agent."
            )
        await db.commit()
        remaining = MAX_VERIFICATION_ATTEMPTS - session.failed_verification_attempts
        await record_audit_event(
            db=db,
            event_type="VERIFICATION_FAILED",
            event_status="FAILURE",
            session_id=session_id,
            call_id=call_id,
            metadata={"attempts": session.failed_verification_attempts, "customer_id": customer_id},
        )
        raise AuthMismatchException(
            f"Customer verification details do not match. {remaining} attempt(s) remaining."
        )

    # 4. Check if session was already assigned to a different customer
    if session.customer_id and session.customer_id != customer_id and session.verified:
        raise VaaniException(
            code="AUTH_MISMATCH",
            message="Session is already verified for a different customer identity.",
            status_code=403,
            retryable=False,
        )

    # 5. Validate DOB
    clean_dob_input = dob.strip()
    clean_cust_dob = customer.dob.strip()

    if clean_dob_input != clean_cust_dob:
        session.failed_verification_attempts += 1
        if session.failed_verification_attempts >= MAX_VERIFICATION_ATTEMPTS:
            session.locked = True
            session.current_state = "LOCKED"
            await db.commit()
            await record_audit_event(
                db=db,
                event_type="VERIFICATION_LOCKED",
                event_status="FAILURE",
                session_id=session_id,
                call_id=call_id,
                metadata={"attempts": session.failed_verification_attempts, "customer_id": customer_id},
            )
            raise LockedSessionException(
                "Session locked due to 3 failed verification attempts. Please contact a human agent."
            )

        await db.commit()
        remaining = MAX_VERIFICATION_ATTEMPTS - session.failed_verification_attempts
        await record_audit_event(
            db=db,
            event_type="VERIFICATION_FAILED",
            event_status="FAILURE",
            session_id=session_id,
            call_id=call_id,
            metadata={"attempts": session.failed_verification_attempts, "customer_id": customer_id},
        )
        raise AuthMismatchException(
            f"Date of birth does not match customer record. {remaining} attempt(s) remaining."
        )

    # 6. Verification Success
    session.customer_id = customer_id
    session.verified = True
    session.current_state = "VERIFIED"
    session.failed_verification_attempts = 0
    session.locked = False

    if call:
        call.customer_id = customer_id

    await record_audit_event(
        db=db,
        event_type="VERIFICATION_SUCCESS",
        event_status="SUCCESS",
        session_id=session_id,
        call_id=call_id,
        metadata={"customer_id": customer_id},
    )

    await db.commit()
    await db.refresh(session)
    return session

