import ssl
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from app.core.config import settings

Base = declarative_base()

_engine: Optional[AsyncEngine] = None
_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


def get_ssl_context() -> ssl.SSLContext:
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    return ssl_context


def get_engine() -> AsyncEngine:
    """Lazily or dynamically get the PostgreSQL Neon engine."""
    global _engine
    if _engine is None:
        if not settings.DATABASE_URL:
            raise RuntimeError(
                "PostgreSQL Neon database not configured! Please provide DATABASE_URL in server/.env"
            )
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            connect_args={"ssl": get_ssl_context()},
            pool_pre_ping=True,
            pool_recycle=300,
        )
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Get the session maker bound to the PostgreSQL engine."""
    global _session_maker
    if _session_maker is None:
        engine = get_engine()
        _session_maker = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI route dependency providing an active PostgreSQL session."""
    if not settings.DATABASE_URL:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PostgreSQL Neon database not configured. Please set DATABASE_URL in server/.env",
        )

    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
