import asyncio
from sqlalchemy import text
from app.db.session import get_engine

TZ_CONVERSIONS = [
    "ALTER TABLE transactions ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE;",
    "ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE;",
    "ALTER TABLE cbs_transactions ALTER COLUMN transaction_date TYPE TIMESTAMP WITH TIME ZONE;",
    "ALTER TABLE sessions ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE;",
    "ALTER TABLE sessions ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE;",
    "ALTER TABLE sessions ALTER COLUMN ended_at TYPE TIMESTAMP WITH TIME ZONE;",
    "ALTER TABLE conversation_turns ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE;",
    "ALTER TABLE escalations ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE;",
    "ALTER TABLE audit_events ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE;",
]

async def check():
    engine = get_engine()
    async with engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        for stmt in TZ_CONVERSIONS:
            await conn.execute(text(stmt))
            print("CONVERTED:", stmt)

    await engine.dispose()
    print("ALL COLUMNS CONVERTED TO TIMESTAMPTZ SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(check())







