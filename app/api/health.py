"""Health check endpoint."""

import datetime

from fastapi import APIRouter

from app.api.schemas import HealthResponse
from app.core.config import settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns:
        Health status with backend and model information
    """
    return HealthResponse(
        status="healthy",
        backend=settings.llm_backend,
        model=settings.resolved_model,
        version=settings.app_version,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )
