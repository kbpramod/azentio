from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import (
    LockedSessionException,
    NotVerifiedException,
    ResourceNotFoundException,
    VaaniException,
)
from app.models.vaani_models import (
    Account,
    CBSTransaction,
    EMISchedule,
    Loan,
    LoanApplication,
    Session,
)
from app.services.audit_service import record_audit_event
from app.services.session_service import get_session


def validate_verified_session(session: Session, target_customer_id: Optional[str] = None) -> None:
    if session.locked:
        raise LockedSessionException("Session is locked due to failed verification attempts.")
    if not session.verified or not session.customer_id:
        raise NotVerifiedException("Customer verification is required before accessing banking records.")
    if target_customer_id and session.customer_id != target_customer_id:
        raise VaaniException(
            code="NOT_VERIFIED",
            message="Unauthorized access: Requested records do not belong to the verified customer.",
            status_code=403,
            retryable=False,
        )


async def get_los_applications(
    db: AsyncSession,
    session_id: str,
    customer_id: str,
) -> List[LoanApplication]:
    session = await get_session(db, session_id)
    validate_verified_session(session, target_customer_id=customer_id)

    result = await db.execute(
        select(LoanApplication).where(LoanApplication.customer_id == customer_id)
    )
    applications = result.scalars().all()

    await record_audit_event(
        db=db,
        event_type="BANKING_TOOL_CALLED",
        event_status="SUCCESS",
        session_id=session_id,
        metadata={"tool": "LOS_APPLICATIONS", "customer_id": customer_id, "count": len(applications)},
    )
    return list(applications)


async def get_lms_loan(
    db: AsyncSession,
    session_id: str,
    loan_id: str,
) -> Loan:
    session = await get_session(db, session_id)
    validate_verified_session(session)

    result = await db.execute(select(Loan).where(Loan.loan_id == loan_id))
    loan = result.scalar_one_or_none()

    if not loan:
        raise ResourceNotFoundException(f"Loan '{loan_id}' not found.")

    if loan.customer_id != session.customer_id:
        raise VaaniException(
            code="NOT_VERIFIED",
            message="Unauthorized: This loan account belongs to another customer.",
            status_code=403,
            retryable=False,
        )

    await record_audit_event(
        db=db,
        event_type="BANKING_TOOL_CALLED",
        event_status="SUCCESS",
        session_id=session_id,
        metadata={"tool": "LMS_LOAN_DETAILS", "loan_id": loan_id},
    )
    return loan


async def get_lms_schedule(
    db: AsyncSession,
    session_id: str,
    loan_id: str,
) -> List[EMISchedule]:
    loan = await get_lms_loan(db, session_id, loan_id)

    result = await db.execute(
        select(EMISchedule)
        .where(EMISchedule.loan_id == loan.loan_id)
        .order_by(EMISchedule.installment_number.asc())
    )
    schedules = result.scalars().all()

    await record_audit_event(
        db=db,
        event_type="BANKING_TOOL_CALLED",
        event_status="SUCCESS",
        session_id=session_id,
        metadata={"tool": "LMS_SCHEDULE", "loan_id": loan_id, "installments": len(schedules)},
    )
    return list(schedules)


async def get_cbs_account(
    db: AsyncSession,
    session_id: str,
    account_id: str,
) -> dict:
    session = await get_session(db, session_id)
    validate_verified_session(session)

    result = await db.execute(select(Account).where(Account.account_id == account_id))
    account = result.scalar_one_or_none()

    if not account:
        raise ResourceNotFoundException(f"Account '{account_id}' not found.")

    if account.customer_id != session.customer_id:
        raise VaaniException(
            code="NOT_VERIFIED",
            message="Unauthorized: This account belongs to another customer.",
            status_code=403,
            retryable=False,
        )

    masked_acc = f"****{account.account_number[-4:]}" if len(account.account_number) >= 4 else "****"

    await record_audit_event(
        db=db,
        event_type="BANKING_TOOL_CALLED",
        event_status="SUCCESS",
        session_id=session_id,
        metadata={"tool": "CBS_ACCOUNT", "account_id": account_id},
    )

    return {
        "account_id": account.account_id,
        "customer_id": account.customer_id,
        "masked_account": masked_acc,
        "account_type": account.account_type,
        "balance": account.balance,
        "currency": account.currency,
        "account_status": account.account_status,
        "source": "CBS-SIMULATED",
    }


async def get_cbs_transaction(
    db: AsyncSession,
    session_id: str,
    transaction_id: str,
) -> CBSTransaction:
    session = await get_session(db, session_id)
    validate_verified_session(session)

    result = await db.execute(
        select(CBSTransaction).where(CBSTransaction.transaction_id == transaction_id)
    )
    tx = result.scalar_one_or_none()

    if not tx:
        raise ResourceNotFoundException(f"Transaction '{transaction_id}' not found.")

    # Check account ownership
    acc_res = await db.execute(select(Account).where(Account.account_id == tx.account_id))
    acc = acc_res.scalar_one_or_none()
    if not acc or acc.customer_id != session.customer_id:
        raise VaaniException(
            code="NOT_VERIFIED",
            message="Unauthorized: This transaction belongs to another customer account.",
            status_code=403,
            retryable=False,
        )

    await record_audit_event(
        db=db,
        event_type="BANKING_TOOL_CALLED",
        event_status="SUCCESS",
        session_id=session_id,
        metadata={"tool": "CBS_TRANSACTION", "transaction_id": transaction_id},
    )
    return tx

