"""API request and response schemas."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    backend: str
    model: str
    version: str
    timestamp: str


class DocumentUploadResponse(BaseModel):
    """Document upload response."""

    document_id: str
    filename: str
    message: str


class DocumentListItem(BaseModel):
    """Document list item."""

    document_id: str
    filename: str
    file_type: str
    file_size: int
    upload_time: str


class DocumentListResponse(BaseModel):
    """Document list response."""

    documents: list[DocumentListItem]
    count: int


class SummarizeRequest(BaseModel):
    """Document summarization request."""

    max_length: int | None = Field(None, description="Maximum length in words")
    style: str | None = Field(None, description="Summary style (e.g., 'brief', 'detailed')")


class SummarizeResponse(BaseModel):
    """Document summarization response."""

    document_id: str
    summary: str


class AskRequest(BaseModel):
    """Document Q&A request."""

    question: str = Field(..., description="Question about the document")


class AskResponse(BaseModel):
    """Document Q&A response."""

    document_id: str
    question: str
    answer: str


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: str | None = None
