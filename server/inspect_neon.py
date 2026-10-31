import asyncio
import time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.db.session import get_ssl_context
from app.models.user import User

async def benchmark():
    engine = create_async_engine(
        settings.DATABASE_URL,
        connect_args={"ssl": get_ssl_context(), "statement_cache_size": 0},
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=False,
    )
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    print("--- 1st query with statement_cache_size=0, pool_pre_ping=False ---")
    t0 = time.perf_counter()
    async with session_maker() as session:
        res = await session.execute(select(User).where(User.email == "customer@azentio.com"))
        user = res.scalar_one_or_none()
        print(f"User: {user.email if user else None}")
    t1 = time.perf_counter()
    print(f"1st query time: {(t1 - t0) * 1000:.2f} ms")

    print("\n--- 2nd query (warm connection) ---")
    t2 = time.perf_counter()
    async with session_maker() as session:
        res = await session.execute(select(User).where(User.email == "customer@azentio.com"))
        user = res.scalar_one_or_none()
    t3 = time.perf_counter()
    print(f"2nd query time: {(t3 - t2) * 1000:.2f} ms")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(benchmark())









