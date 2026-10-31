from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select, text
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


class PayEmiRequest(BaseModel):
    loan_id: str = Field(..., description="Loan ID e.g. LN-501")
    amount: float = Field(..., gt=0, description="EMI amount to pay")


@router.get("/account", response_model=UserOut, summary="Get customer account summary")
async def get_account(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.get("/accounts", summary="Get all linked bank accounts from Neon database")
async def get_all_linked_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieve all savings, salary, and checking accounts from Neon DB."""
    accounts = [
        {
            "account_id": current_user.account_number,
            "type": "Primary Checking",
            "balance": current_user.balance,
            "currency": "INR",
            "status": "ACTIVE",
            "is_primary": True,
        }
    ]

    try:
        res = await db.execute(text("SELECT account_id, customer_id, type, balance, currency FROM accounts LIMIT 10;"))
        for row in res.fetchall():
            m = dict(row._mapping)
            accounts.append({
                "account_id": m["account_id"],
                "type": f"{m['type'].capitalize()} Account",
                "balance": float(m["balance"]),
                "currency": m.get("currency", "INR"),
                "status": "ACTIVE",
                "is_primary": False,
            })
    except Exception:
        pass

    return accounts


@router.get("/loans", summary="Get customer loans and EMI schedules from Neon database")
async def get_customer_loans(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Fetch active vehicle, personal, and home loans with their EMI schedules."""
    loans_list = []
    try:
        loans_res = await db.execute(
            text("SELECT loan_id, customer_id, product, principal, outstanding, emi_amount, next_due_date, overdue_amount, status FROM loans LIMIT 10;")
        )
        for r in loans_res.fetchall():
            m = dict(r._mapping)
            loan_id = m["loan_id"]

            # Fetch EMI schedule for this loan
            sched_res = await db.execute(
                text(f"SELECT n, due_date, amount, status FROM emi_schedule WHERE loan_id = '{loan_id}' ORDER BY n LIMIT 12;")
            )
            schedule = [
                {
                    "installment_no": s[0],
                    "due_date": s[1].isoformat() if hasattr(s[1], "isoformat") else str(s[1]),
                    "amount": float(s[2]),
                    "status": s[3],
                }
                for s in sched_res.fetchall()
            ]

            loans_list.append({
                "loan_id": m["loan_id"],
                "product": f"{m['product'].capitalize()} Loan",
                "principal": float(m["principal"]),
                "outstanding": float(m["outstanding"]),
                "emi_amount": float(m["emi_amount"]),
                "next_due_date": m["next_due_date"].isoformat() if hasattr(m["next_due_date"], "isoformat") else str(m["next_due_date"]),
                "overdue_amount": float(m["overdue_amount"]),
                "status": m["status"],
                "schedule": schedule,
            })
    except Exception as e:
        print("Error fetching loans from Neon:", e)

    return loans_list


@router.post("/pay-emi", summary="Pay monthly EMI installment")
async def pay_emi_installment(
    payload: PayEmiRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    if current_user.balance < payload.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient balance to pay EMI. Available: ₹{current_user.balance:,.2f}",
        )

    current_user.balance -= payload.amount

    # Update loan outstanding in Neon DB if exists
    try:
        await db.execute(
            text(f"UPDATE loans SET outstanding = GREATEST(0, outstanding - {int(payload.amount)}) WHERE loan_id = '{payload.loan_id}';")
        )
        await db.execute(
            text(f"UPDATE emi_schedule SET status = 'PAID' WHERE loan_id = '{payload.loan_id}' AND status != 'PAID' LIMIT 1;")
        )
    except Exception:
        pass

    # Audit transaction
    tx = Transaction(
        user_id=current_user.id,
        type="transfer_out",
        amount=payload.amount,
        description=f"Monthly EMI Repayment - {payload.loan_id}",
        status="completed",
    )
    db.add(tx)
    await db.commit()

    return {
        "success": True,
        "message": f"EMI payment of ₹{payload.amount:,.2f} for loan {payload.loan_id} processed successfully.",
        "remaining_balance": current_user.balance,
    }


@router.get(
    "/transactions",
    summary="List customer transaction history from Neon DB",
)
async def list_transactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    all_txs = []

    # 1. Fetch from app transactions
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(desc(Transaction.created_at))
        .limit(50)
    )
    for t in result.scalars().all():
        all_txs.append({
            "id": f"TXN-{t.id}",
            "type": t.type,
            "amount": t.amount,
            "description": t.description,
            "status": t.status,
            "created_at": t.created_at.isoformat() if hasattr(t.created_at, "isoformat") else str(t.created_at),
        })

    # 2. Also incorporate bank_transactions from Neon
    try:
        bt_res = await db.execute(
            text("SELECT txn_id, account_id, date, amount, direction, status, merchant FROM bank_transactions ORDER BY date DESC LIMIT 20;")
        )
        for r in bt_res.fetchall():
            m = dict(r._mapping)
            all_txs.append({
                "id": m["txn_id"],
                "type": "deposit" if m["direction"] == "credit" else "transfer_out",
                "amount": float(m["amount"]),
                "description": f"{m.get('merchant', 'Transfer')} ({m.get('account_id', '')})",
                "status": m["status"].lower(),
                "created_at": f"{m['date']}T10:00:00",
            })
    except Exception:
        pass

    return all_txs


@router.post(
    "/transfer",
    response_model=TransactionOut,
    summary="Transfer funds to another account / UPI ID",
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
            detail=f"Insufficient funds. Current balance: ₹{current_user.balance:,.2f}",
        )

    # Deduct from sender
    current_user.balance -= payload.amount

    # Credit recipient if found
    result = await db.execute(
        select(User).where(User.account_number == payload.recipient_account)
    )
    recipient = result.scalar_one_or_none()
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
