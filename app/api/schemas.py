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


class MultiAskRequest(BaseModel):
    """Multi-document Q&A request."""

    document_ids: list[str] = Field(..., description="List of document IDs to query")
    question: str = Field(..., description="Question to ask across all documents")


class MultiAskResponse(BaseModel):
    """Multi-document Q&A response."""

    document_ids: list[str]
    question: str
    answer: str


class MultiSummarizeRequest(BaseModel):
    """Multi-document summarization request."""

    document_ids: list[str] = Field(..., description="List of document IDs to summarize")
    max_length: int | None = Field(None, description="Maximum length in words")
    style: str | None = Field(None, description="Summary style (e.g., 'brief', 'detailed')")


class MultiSummarizeResponse(BaseModel):
    """Multi-document summarization response."""

    document_ids: list[str]
    summary: str


class DeleteDocumentResponse(BaseModel):
    """Document deletion response."""

    document_id: str
    message: str


class UsageStatsResponse(BaseModel):
    """Usage stats response."""

    document_count: int
    total_size_bytes: int
    total_size_mb: float
    file_types: dict[str, int]


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: str | None = None
