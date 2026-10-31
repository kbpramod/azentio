from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings
from app.core.exceptions import VaaniException, vaani_exception_handler
from app.db.seed import seed_synthetic_data
from app.db.session import get_engine


async def init_database() -> None:
    """Create database tables and seed repeatable synthetic banking data."""
    try:
        await seed_synthetic_data()
    except Exception as e:
        print(f"Database initialization warning: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    print(f"Starting {settings.PROJECT_NAME} (VaaniDesk Backend)...")
    await init_database()
    yield
    print(f"Shutting down {settings.PROJECT_NAME}...")
    try:
        engine = get_engine()
        await engine.dispose()
    except Exception:
        pass


def create_application() -> FastAPI:
    """FastAPI application factory."""
    application = FastAPI(
        title=settings.PROJECT_NAME,
        description=(
            "VaaniDesk AI-Powered Voice Customer Service Banking Assistant API. "
            "Includes server-side voice sessions, customer verification, mock LOS, LMS, CBS, "
            "CSM ticket management, and operations dashboard."
        ),
        version="1.0.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Register VaaniDesk custom error handler
    application.add_exception_handler(VaaniException, vaani_exception_handler)

    # CORS configuration
    if settings.BACKEND_CORS_ORIGINS:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Canonical VaaniDesk Infrastructure Health Endpoint
    @application.get("/health", tags=["Health"])
    async def canonical_health():
        return {
            "status": "ok",
            "service": "vaanidesk-backend",
        }

    # Root welcome & service catalog
    @application.get("/", tags=["Root"])
    async def root():
        return {
            "message": f"Welcome to {settings.PROJECT_NAME}",
            "system": "VaaniDesk AI Voice Assistant & Banking System",
            "status": "online",
            "database": "SQLite Local (Active)" if "sqlite" in settings.DATABASE_URL else "PostgreSQL Neon",
            "version": "1.0.0",
            "docs": "/docs",
            "redoc": "/redoc",
            "canonical_health": "/health",
            "api_v1_health": f"{settings.API_V1_STR}/health",
            "sessions": {
                "create": f"{settings.API_V1_STR}/sessions",
                "verify": f"{settings.API_V1_STR}/sessions/{{session_id}}/verify",
                "turn": f"{settings.API_V1_STR}/sessions/{{session_id}}/turn",
                "escalate": f"{settings.API_V1_STR}/sessions/{{session_id}}/escalate",
                "end": f"{settings.API_V1_STR}/sessions/{{session_id}}/end",
            },
            "mock_banking": {
                "los_applications": f"{settings.API_V1_STR}/mock/los/applications",
                "lms_loans": f"{settings.API_V1_STR}/mock/lms/loans/{{loan_id}}",
                "lms_schedule": f"{settings.API_V1_STR}/mock/lms/loans/{{loan_id}}/schedule",
                "cbs_accounts": f"{settings.API_V1_STR}/mock/cbs/accounts/{{account_id}}",
                "cbs_transactions": f"{settings.API_V1_STR}/mock/cbs/transactions/{{transaction_id}}",
                "csm_tickets": f"{settings.API_V1_STR}/mock/csm/tickets",
            },
            "operations": {
                "calls": f"{settings.API_V1_STR}/ops/calls",
                "tickets": f"{settings.API_V1_STR}/ops/tickets",
                "escalations": f"{settings.API_V1_STR}/ops/escalations",
            },
        }

    # Include API Routers under /api/v1
    application.include_router(api_router, prefix=settings.API_V1_STR)

    return application


app = create_application()
