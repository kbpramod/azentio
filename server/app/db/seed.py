"""Repeatable Synthetic Data Seeding for VaaniDesk Banking Assistant.

Safe to execute multiple times without record duplication.
Includes fictional banking entities for:
- Customers (DOB verification, lockout testing)
- Loan Applications (LOS with pending documents)
- Active & Overdue Loans (LMS balance and status)
- EMI Schedules (Repayment installments)
- Accounts & Transactions (CBS)
- Service Tickets (CSM)
- Demo Portal Customer User
"""

import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from app.core.security import hash_password
from app.db.session import Base, get_engine, get_session_maker
from app.models.transaction import Transaction
from app.models.user import User
from app.models.vaani_models import (
    Account,
    CBSTransaction,
    Customer,
    EMISchedule,
    Loan,
    LoanApplication,
    Ticket,
)


def utcnow():
    return datetime.now(timezone.utc)


async def seed_synthetic_data() -> None:
    engine = get_engine()
    # Create tables if not existing
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = get_session_maker()
    async with session_maker() as session:
        # 1. Seed Portal Demo User (Alex Mercer)
        user_res = await session.execute(
            select(User).where(User.email == "customer@azentio.com")
        )
        demo_user = user_res.scalar_one_or_none()
        if not demo_user:
            demo_user = User(
                email="customer@azentio.com",
                full_name="Alex Mercer",
                hashed_password=hash_password("password123"),
                role="customer",
                account_number="AZ-882194",
                balance=3450.75,
                ai_credits=500,
                is_active=True,
            )
            session.add(demo_user)
            await session.flush()

            tx1 = Transaction(
                user_id=demo_user.id,
                type="deposit",
                amount=3000.00,
                description="Salary Direct Deposit - Azentio Corp",
                status="completed",
            )
            tx2 = Transaction(
                user_id=demo_user.id,
                type="transfer_out",
                amount=45.25,
                description="Coffee & Bakery Mart",
                status="completed",
            )
            session.add_all([tx1, tx2])

        # 2. Seed Customers
        customers_data = [
            {
                "customer_id": "C1023",
                "customer_name": "Alex Mercer",
                "dob": "1995-03-12",
                "phone_number": "+1-555-0192",
                "email": "customer@azentio.com",
            },
            {
                "customer_id": "C1024",
                "customer_name": "Priya Sharma",
                "dob": "1990-08-25",
                "phone_number": "+1-555-0144",
                "email": "priya.sharma@example.com",
            },
            {
                "customer_id": "C1099",
                "customer_name": "Lockout Test Subject",
                "dob": "1985-01-01",
                "phone_number": "+1-555-0199",
                "email": "lockout.test@example.com",
            },
        ]
        for c in customers_data:
            exists = (await session.execute(
                select(Customer).where(Customer.customer_id == c["customer_id"])
            )).scalar_one_or_none()
            if not exists:
                session.add(Customer(**c))
        await session.flush()

        # 3. Seed Loan Applications (LOS)
        applications_data = [
            {
                "application_id": "APP-77",
                "customer_id": "C1023",
                "product_type": "personal",
                "requested_amount": 300000.0,
                "application_status": "DOC_VERIFICATION",
                "pending_documents": ["salary_slip"],
            },
            {
                "application_id": "APP-70",
                "customer_id": "C1023",
                "product_type": "home_loan",
                "requested_amount": 2500000.0,
                "application_status": "APPROVED",
                "pending_documents": [],
            },
            {
                "application_id": "APP-88",
                "customer_id": "C1024",
                "product_type": "auto_loan",
                "requested_amount": 750000.0,
                "application_status": "CREDIT_REVIEW",
                "pending_documents": ["address_proof"],
            },
        ]
        for app in applications_data:
            exists = (await session.execute(
                select(LoanApplication).where(LoanApplication.application_id == app["application_id"])
            )).scalar_one_or_none()
            if not exists:
                session.add(LoanApplication(**app))
        await session.flush()

        # 4. Seed Loans (LMS)
        loans_data = [
            {
                "loan_id": "LN-9012",
                "customer_id": "C1023",
                "product_type": "home_loan",
                "principal": 3000000.0,
                "outstanding_amount": 2450000.0,
                "emi_amount": 28500.0,
                "next_due_date": "2026-11-05",
                "overdue_amount": 0.0,
                "loan_status": "ACTIVE",
            },
            {
                "loan_id": "LN-9013",
                "customer_id": "C1023",
                "product_type": "personal",
                "principal": 100000.0,
                "outstanding_amount": 45000.0,
                "emi_amount": 5000.0,
                "next_due_date": "2026-11-01",
                "overdue_amount": 2500.0,
                "loan_status": "ACTIVE",
            },
            {
                "loan_id": "LN-9020",
                "customer_id": "C1024",
                "product_type": "auto_loan",
                "principal": 800000.0,
                "outstanding_amount": 600000.0,
                "emi_amount": 15000.0,
                "next_due_date": "2026-11-10",
                "overdue_amount": 0.0,
                "loan_status": "ACTIVE",
            },
        ]
        for ln in loans_data:
            exists = (await session.execute(
                select(Loan).where(Loan.loan_id == ln["loan_id"])
            )).scalar_one_or_none()
            if not exists:
                session.add(Loan(**ln))
        await session.flush()

        # 5. Seed EMI Schedules (LMS)
        schedules_data = [
            {
                "loan_id": "LN-9012",
                "installment_number": 1,
                "due_date": "2026-10-05",
                "amount": 28500.0,
                "payment_status": "PAID",
            },
            {
                "loan_id": "LN-9012",
                "installment_number": 2,
                "due_date": "2026-11-05",
                "amount": 28500.0,
                "payment_status": "DUE",
            },
            {
                "loan_id": "LN-9012",
                "installment_number": 3,
                "due_date": "2026-12-05",
                "amount": 28500.0,
                "payment_status": "DUE",
            },
        ]
        for sch in schedules_data:
            exists = (await session.execute(
                select(EMISchedule).where(
                    (EMISchedule.loan_id == sch["loan_id"]) &
                    (EMISchedule.installment_number == sch["installment_number"])
                )
            )).scalar_one_or_none()
            if not exists:
                session.add(EMISchedule(**sch))
        await session.flush()

        # 6. Seed Accounts (CBS)
        accounts_data = [
            {
                "account_id": "ACC-1001",
                "customer_id": "C1023",
                "account_type": "savings",
                "balance": 145000.50,
                "currency": "INR",
            },
            {
                "account_id": "ACC-1002",
                "customer_id": "C1024",
                "account_type": "checking",
                "balance": 82500.00,
                "currency": "INR",
            },
        ]
        for acc in accounts_data:
            exists = (await session.execute(
                select(Account).where(Account.account_id == acc["account_id"])
            )).scalar_one_or_none()
            if not exists:
                session.add(Account(**acc))
        await session.flush()

        # 7. Seed Transactions (CBS)
        txs_data = [
            {
                "transaction_id": "TX-5501",
                "account_id": "ACC-1001",
                "amount": 4500.0,
                "transaction_type": "DEBIT",
                "transaction_status": "SUCCESS",
                "transaction_date": utcnow(),
                "merchant_description": "Supermarket Retail Hub",
            },
            {
                "transaction_id": "TX-5502",
                "account_id": "ACC-1001",
                "amount": 50000.0,
                "transaction_type": "CREDIT",
                "transaction_status": "SUCCESS",
                "transaction_date": utcnow(),
                "merchant_description": "Employer Direct Deposit",
            },
            {
                "transaction_id": "TX-5503",
                "account_id": "ACC-1002",
                "amount": 1200.0,
                "transaction_type": "DEBIT",
                "transaction_status": "SUCCESS",
                "transaction_date": utcnow(),
                "merchant_description": "Coffee & Bistro",
            },
        ]
        for tx in txs_data:
            exists = (await session.execute(
                select(CBSTransaction).where(CBSTransaction.transaction_id == tx["transaction_id"])
            )).scalar_one_or_none()
            if not exists:
                session.add(CBSTransaction(**tx))
        await session.flush()

        # 8. Seed Sample CSM Ticket
        sample_ticket = {
            "ticket_id": "SR-4001",
            "customer_id": "C1023",
            "ticket_type": "service_request",
            "category": "address_update",
            "summary": "Customer requested mailing address change confirmation",
            "priority": "NORMAL",
            "status": "RESOLVED",
            "idempotency_key": "INIT-SEED-TICKET-1",
        }
        exists_ticket = (await session.execute(
            select(Ticket).where(Ticket.idempotency_key == sample_ticket["idempotency_key"])
        )).scalar_one_or_none()
        if not exists_ticket:
            session.add(Ticket(**sample_ticket))

        await session.commit()
        print("Repeatable synthetic banking dataset initialized and verified successfully.")


async def main():
    await seed_synthetic_data()
    engine = get_engine()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
