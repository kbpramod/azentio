from datetime import datetime, timezone
from fastapi import APIRouter
from app.core.config import settings
from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Service Health Check")
async def health_check() -> HealthResponse:
    """Return health and status information about the backend service."""
    return HealthResponse(
        status="ok",
        app_name=settings.PROJECT_NAME,
        version="0.1.0",
        environment="development" if settings.DEBUG else "production",
        timestamp=datetime.now(timezone.utc),
    )

