from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from app.api.v1.api import api_router
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import Base, get_engine, get_session_maker
from app.models.transaction import Transaction
from app.models.user import User


async def init_database() -> None:
    """Create database tables and seed initial demo data in PostgreSQL Neon."""
    if not settings.DATABASE_URL:
        print("\n" + "=" * 70)
        print(" [DATABASE CONFIGURATION REQUIRED]")
        print(" Neon PostgreSQL DATABASE_URL is not set in server/.env.")
        print(" Please paste your Neon connection string into server/.env:")
        print(' DATABASE_URL="postgresql://username:password@ep-xyz.neon.tech/neondb?sslmode=require"')
        print("=" * 70 + "\n")
        return

    print("Connecting to PostgreSQL Neon cluster...")
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("PostgreSQL Neon tables verified and migrations ready.")

    # Check and seed default demo customer in Neon
    session_maker = get_session_maker()
    async with session_maker() as session:
        result = await session.execute(
            select(User).where(User.email == "customer@azentio.com")
        )
        existing = result.scalar_one_or_none()
        if not existing:
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
            tx3 = Transaction(
                user_id=demo_user.id,
                type="deposit",
                amount=500.00,
                description="Mobile Check Deposit",
                status="completed",
            )
            session.add_all([tx1, tx2, tx3])
            await session.commit()
            print("Successfully seeded demo customer into PostgreSQL Neon: customer@azentio.com")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    print(f"Starting {settings.PROJECT_NAME}...")
    try:
        await init_database()
    except Exception as e:
        print(f"PostgreSQL Neon connection error: {e}")
    yield
    print(f"Shutting down {settings.PROJECT_NAME}...")
    if settings.DATABASE_URL:
        try:
            engine = get_engine()
            await engine.dispose()
        except Exception:
            pass


def create_application() -> FastAPI:
    """FastAPI application factory."""
    application = FastAPI(
        title=settings.PROJECT_NAME,
        description="Azentio Banking System API connected to PostgreSQL Neon with AI Credits and Customer Agent.",
        version="1.0.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS configuration
    if settings.BACKEND_CORS_ORIGINS:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Include API Routers
    application.include_router(api_router, prefix=settings.API_V1_STR)

    @application.get("/", tags=["Root"])
    async def root():
        return {
            "message": f"Welcome to {settings.PROJECT_NAME}",
            "system": settings.PROJECT_NAME,
            "status": "online",
            "database": "PostgreSQL Neon Connected" if settings.DATABASE_URL else "Waiting for DATABASE_URL in server/.env",
            "version": "1.0.0",
            "docs": "/docs",
            "health": f"{settings.API_V1_STR}/health",
            "auth": {
                "login": f"{settings.API_V1_STR}/auth/login",
                "register": f"{settings.API_V1_STR}/auth/register",
                "demo_account": {
                    "email": "customer@azentio.com",
                    "password": "password123",
                },
            },
        }

    return application


app = create_application()
