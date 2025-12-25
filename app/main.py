"""Main FastAPI application."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.documents import router as documents_router
from app.api.errors import (
    DocumentNotFoundError,
    LLMBackendError,
    UnsupportedFileTypeError,
    document_not_found_handler,
    llm_backend_error_handler,
    unsupported_file_type_handler,
)
from app.api.health import router as health_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager."""
    # Startup
    setup_logging()
    logger.info(f"Starting InferDocs v{settings.app_version}")
    logger.info(f"LLM Backend: {settings.llm_backend}")
    logger.info(f"Model: {settings.resolved_model}")

    yield

    # Shutdown
    logger.info("Shutting down InferDocs")


# Create FastAPI app
app = FastAPI(
    title="InferDocs",
    description="Local Document Q&A & Summarization Service",
    version=settings.app_version,
    lifespan=lifespan,
)

# Register error handlers
app.add_exception_handler(DocumentNotFoundError, document_not_found_handler)  # type: ignore[arg-type]
app.add_exception_handler(UnsupportedFileTypeError, unsupported_file_type_handler)  # type: ignore[arg-type]
app.add_exception_handler(LLMBackendError, llm_backend_error_handler)  # type: ignore[arg-type]

# Register routers
app.include_router(health_router)
app.include_router(documents_router)


# Playground endpoint
@app.get("/playground")
async def playground() -> FileResponse:
    """Serve the playground HTML page."""
    return FileResponse("web/playground.html")


# Static files for playground
app.mount("/static", StaticFiles(directory="web"), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "dev",
    )
