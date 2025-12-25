"""API error handlers."""

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class DocumentNotFoundError(Exception):
    """Raised when a document is not found."""

    def __init__(self, document_id: str) -> None:
        """Initialize error."""
        self.document_id = document_id
        super().__init__(f"Document not found: {document_id}")


class UnsupportedFileTypeError(Exception):
    """Raised when a file type is not supported."""

    def __init__(self, file_type: str) -> None:
        """Initialize error."""
        self.file_type = file_type
        super().__init__(f"Unsupported file type: {file_type}")


class LLMBackendError(Exception):
    """Raised when LLM backend encounters an error."""

    def __init__(self, message: str) -> None:
        """Initialize error."""
        super().__init__(message)


async def document_not_found_handler(
    request: Request, exc: DocumentNotFoundError
) -> JSONResponse:
    """Handle DocumentNotFoundError."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": "Document not found", "detail": str(exc)},
    )


async def unsupported_file_type_handler(
    request: Request, exc: UnsupportedFileTypeError
) -> JSONResponse:
    """Handle UnsupportedFileTypeError."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "Unsupported file type", "detail": str(exc)},
    )


async def llm_backend_error_handler(
    request: Request, exc: LLMBackendError
) -> JSONResponse:
    """Handle LLMBackendError."""
    logger.error(f"LLM backend error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "LLM backend error", "detail": str(exc)},
    )
