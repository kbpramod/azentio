from typing import List, Optional
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import VaaniException
from app.db.session import get_db
from app.schemas.vaani_schemas import (
    AccountOut,
    CBSTransactionOut,
    LMSScheduleResponse,
    LoanApplicationOut,
    LoanOut,
    LOSResponse,
)
from app.services.banking_service import (
    get_cbs_account,
    get_cbs_transaction,
    get_lms_loan,
    get_lms_schedule,
    get_los_applications,
)

router = APIRouter()


def extract_session_id(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    session_id: Optional[str] = Query(None),
) -> str:
    sid = x_session_id or session_id
    if not sid:
        raise VaaniException(
            code="NOT_VERIFIED",
            message="Active session ID is required via 'X-Session-ID' header or 'session_id' query param.",
            status_code=403,
            retryable=False,
        )
    return sid


# ---------------- LOS Mock Endpoints ----------------

@router.get(
    "/los/applications",
    response_model=LOSResponse,
    summary="Mock LOS: Get loan applications for authenticated customer",
)
async def api_get_los_applications(
    customer_id: str = Query(..., description="Customer ID to retrieve applications for"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    session_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> LOSResponse:
    active_sid = extract_session_id(x_session_id, session_id)
    apps = await get_los_applications(db=db, session_id=active_sid, customer_id=customer_id)
    return LOSResponse(
        customer_id=customer_id,
        applications=[LoanApplicationOut.model_validate(a) for a in apps],
        source="LOS-SIMULATED",
    )


# ---------------- LMS Mock Endpoints ----------------

@router.get(
    "/lms/loans/{loan_id}",
    response_model=LoanOut,
    summary="Mock LMS: Retrieve loan details and outstanding balance",
)
async def api_get_lms_loan(
    loan_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    session_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> LoanOut:
    active_sid = extract_session_id(x_session_id, session_id)
    loan = await get_lms_loan(db=db, session_id=active_sid, loan_id=loan_id)
    return LoanOut(
        loan_id=loan.loan_id,
        customer_id=loan.customer_id,
        application_id=loan.application_id,
        product_type=loan.product_type,
        outstanding_amount=loan.outstanding_amount,
        emi_amount=loan.emi_amount,
        next_due_date=loan.next_due_date,
        overdue_amount=loan.overdue_amount,
        loan_status=loan.loan_status,
        source="LMS-SIMULATED",
    )


@router.get(
    "/lms/loans/{loan_id}/schedule",
    response_model=LMSScheduleResponse,
    summary="Mock LMS: Retrieve loan repayment schedule",
)
async def api_get_lms_schedule(
    loan_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    session_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> LMSScheduleResponse:
    active_sid = extract_session_id(x_session_id, session_id)
    schedules = await get_lms_schedule(db=db, session_id=active_sid, loan_id=loan_id)
    return LMSScheduleResponse(
        loan_id=loan_id,
        schedule=schedules,
        source="LMS-SIMULATED",
    )


# ---------------- CBS Mock Endpoints ----------------

@router.get(
    "/cbs/accounts/{account_id}",
    response_model=AccountOut,
    summary="Mock CBS: Retrieve account balance with masked identifier",
)
async def api_get_cbs_account(
    account_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    session_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> AccountOut:
    active_sid = extract_session_id(x_session_id, session_id)
    account_data = await get_cbs_account(db=db, session_id=active_sid, account_id=account_id)
    return AccountOut(**account_data)


@router.get(
    "/cbs/transactions/{transaction_id}",
    response_model=CBSTransactionOut,
    summary="Mock CBS: Retrieve transaction details",
)
async def api_get_cbs_transaction(
    transaction_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    session_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> CBSTransactionOut:
    active_sid = extract_session_id(x_session_id, session_id)
    tx = await get_cbs_transaction(db=db, session_id=active_sid, transaction_id=transaction_id)
    return CBSTransactionOut(
        transaction_id=tx.transaction_id,
        account_id=tx.account_id,
        amount=tx.amount,
        transaction_type=tx.transaction_type,
        transaction_status=tx.transaction_status,
        transaction_date=tx.transaction_date,
        merchant_description=tx.merchant_description,
        source="CBS-SIMULATED",
    )

