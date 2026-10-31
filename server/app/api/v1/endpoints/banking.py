from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.auth import TransactionOut, TransferRequest, UserOut
from pydantic import BaseModel, Field

router = APIRouter()


class DepositRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to deposit")
    note: str = Field("Direct Deposit", max_length=100)


@router.get("/account", response_model=UserOut, summary="Get customer account summary")
async def get_account(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.get(
    "/transactions",
    response_model=List[TransactionOut],
    summary="List customer transaction history",
)
async def list_transactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[TransactionOut]:
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(desc(Transaction.created_at))
        .limit(50)
    )
    transactions = result.scalars().all()
    return [TransactionOut.model_validate(t) for t in transactions]


@router.post(
    "/transfer",
    response_model=TransactionOut,
    summary="Transfer funds to another account",
)
async def transfer_funds(
    payload: TransferRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TransactionOut:
    if current_user.account_number == payload.recipient_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transfer funds to the same account.",
        )

    if current_user.balance < payload.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient funds. Current balance: ${current_user.balance:,.2f}",
        )

    # Check recipient
    result = await db.execute(
        select(User).where(User.account_number == payload.recipient_account)
    )
    recipient = result.scalar_one_or_none()

    # Deduct from sender
    current_user.balance -= payload.amount

    # Credit recipient if found
    if recipient:
        recipient.balance += payload.amount
        recipient_tx = Transaction(
            user_id=recipient.id,
            type="transfer_in",
            amount=payload.amount,
            description=f"Received from {current_user.account_number} ({payload.note})",
            status="completed",
        )
        db.add(recipient_tx)

    # Sender transaction
    sender_tx = Transaction(
        user_id=current_user.id,
        type="transfer_out",
        amount=payload.amount,
        description=f"Transfer to {payload.recipient_account} ({payload.note})",
        status="completed",
    )
    db.add(sender_tx)

    await db.commit()
    await db.refresh(sender_tx)
    return TransactionOut.model_validate(sender_tx)


@router.post(
    "/deposit",
    response_model=TransactionOut,
    summary="Deposit funds into customer account",
)
async def deposit_funds(
    payload: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TransactionOut:
    current_user.balance += payload.amount

    tx = Transaction(
        user_id=current_user.id,
        type="deposit",
        amount=payload.amount,
        description=payload.note,
        status="completed",
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return TransactionOut.model_validate(tx)

