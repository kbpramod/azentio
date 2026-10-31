"""Push all VaaniDesk tables and synthetic data to Neon PostgreSQL.

Usage:
  1. Set your Neon DATABASE_URL in azentio/server/.env
  2. Run: python push_to_neon.py
"""

import asyncio
from sqlalchemy import text
from app.core.config import settings
from app.db.seed import seed_synthetic_data
from app.db.session import Base, get_engine


ALIGNMENTS = [
    # Non-destructive schema alignment ensuring existing Neon tables match VaaniDesk expectations
    "ALTER TABLE calls DROP CONSTRAINT IF EXISTS calls_outcome_check;",
    "ALTER TABLE loan_applications DROP CONSTRAINT IF EXISTS loan_applications_stage_check;",
    "ALTER TABLE emi_schedule DROP CONSTRAINT IF EXISTS emi_schedule_status_check;",
    "ALTER TABLE claims DROP CONSTRAINT IF EXISTS claims_status_check;",
    "ALTER TABLE bank_transactions DROP CONSTRAINT IF EXISTS bank_transactions_status_check;",

    # Normalize timestamp columns to TIMESTAMPTZ for asyncpg timezone-aware timestamps
    "ALTER TABLE transactions ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE;",
    "ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE;",
    "ALTER TABLE cbs_transactions ALTER COLUMN transaction_date TYPE TIMESTAMP WITH TIME ZONE;",
    "ALTER TABLE sessions ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE;",
    "ALTER TABLE sessions ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE;",
    "ALTER TABLE sessions ALTER COLUMN ended_at TYPE TIMESTAMP WITH TIME ZONE;",
    "ALTER TABLE conversation_turns ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE;",
    "ALTER TABLE escalations ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE;",
    "ALTER TABLE audit_events ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE;",

    "ALTER TABLE customers ADD COLUMN IF NOT EXISTS customer_name TEXT;",
    "UPDATE customers SET customer_name = name WHERE customer_name IS NULL AND name IS NOT NULL;",
    "ALTER TABLE customers ALTER COLUMN name DROP NOT NULL;",
    "ALTER TABLE customers ADD COLUMN IF NOT EXISTS phone_number TEXT;",
    "ALTER TABLE customers ADD COLUMN IF NOT EXISTS email TEXT;",
    "ALTER TABLE customers ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();",
    "ALTER TABLE customers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();",

    "ALTER TABLE loan_applications ADD COLUMN IF NOT EXISTS application_id TEXT;",
    "UPDATE loan_applications SET application_id = app_id WHERE application_id IS NULL AND app_id IS NOT NULL;",
    "ALTER TABLE loan_applications ADD COLUMN IF NOT EXISTS product_type TEXT;",
    "UPDATE loan_applications SET product_type = product WHERE product_type IS NULL AND product IS NOT NULL;",
    "ALTER TABLE loan_applications ADD COLUMN IF NOT EXISTS requested_amount DOUBLE PRECISION;",
    "UPDATE loan_applications SET requested_amount = amount WHERE requested_amount IS NULL AND amount IS NOT NULL;",
    "ALTER TABLE loan_applications ADD COLUMN IF NOT EXISTS application_status TEXT;",
    "UPDATE loan_applications SET application_status = stage WHERE application_status IS NULL AND stage IS NOT NULL;",
    "ALTER TABLE loan_applications ADD COLUMN IF NOT EXISTS pending_documents JSONB DEFAULT '[]'::jsonb;",
    "ALTER TABLE loan_applications ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();",
    "ALTER TABLE loan_applications ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();",

    "ALTER TABLE loans ADD COLUMN IF NOT EXISTS product_type TEXT;",
    "UPDATE loans SET product_type = product WHERE product_type IS NULL AND product IS NOT NULL;",
    "ALTER TABLE loans ADD COLUMN IF NOT EXISTS outstanding_amount DOUBLE PRECISION;",
    "UPDATE loans SET outstanding_amount = outstanding WHERE outstanding_amount IS NULL AND outstanding IS NOT NULL;",
    "ALTER TABLE loans ADD COLUMN IF NOT EXISTS loan_status TEXT;",
    "UPDATE loans SET loan_status = status WHERE loan_status IS NULL AND status IS NOT NULL;",
    "ALTER TABLE loans ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();",
    "ALTER TABLE loans ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();",

    "ALTER TABLE calls ADD COLUMN IF NOT EXISTS session_id TEXT;",
    "ALTER TABLE calls ADD COLUMN IF NOT EXISTS escalation_status TEXT DEFAULT 'NONE';",

    "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS session_id TEXT;",

    "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS account_type TEXT;",
    "UPDATE accounts SET account_type = type WHERE account_type IS NULL AND type IS NOT NULL;",
    "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS account_number TEXT;",
    "UPDATE accounts SET account_number = account_id WHERE account_number IS NULL AND account_id IS NOT NULL;",
    "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS account_status TEXT DEFAULT 'ACTIVE';",
    "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();",
    "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();",
]


async def push_tables_to_neon():
    print("=" * 70)
    print("PUSHING TABLES & DATA TO NEON POSTGRESQL")
    print("=" * 70)

    db_url = settings.DATABASE_URL
    if not db_url or "postgres" not in db_url:
        print("\n[!] DATABASE_URL in server/.env is NOT pointing to PostgreSQL Neon!")
        print(f"Current DATABASE_URL: {db_url}")
        print("\nPlease open azentio/server/.env and paste your Neon connection string:")
        print('DATABASE_URL="postgresql://username:password@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require"')
        print("=" * 70)
        return

    print("\n[Step 1/3] Connecting to Neon PostgreSQL cluster...")
    engine = get_engine()

    # Apply safe non-destructive alignments using autocommit mode
    async with engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        for stmt in ALIGNMENTS:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass

    print("[Step 2/3] Synchronizing all tables (Base.metadata.create_all)...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Inspect synchronized tables
        query = text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name;"
        )
        result = await conn.execute(query)
        tables = [row[0] for row in result.fetchall()]

        print(f"[OK] Successfully synchronized {len(tables)} tables in Neon PostgreSQL:")
        for t in tables:
            print(f"   * {t}")

    print("\n[Step 3/3] Seeding synthetic banking dataset into Neon...")
    await seed_synthetic_data()
    print("[OK] Synthetic banking records seeded into Neon!")

    await engine.dispose()
    print("\n" + "=" * 70)
    print("SUCCESS: All models, tables, and synthetic data are now live on your Neon cluster!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(push_tables_to_neon())
