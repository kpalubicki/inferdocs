"""Document management endpoints."""

from collections.abc import AsyncIterator

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.errors import DocumentNotFoundError, UnsupportedFileTypeError
from app.api.schemas import (
    AskRequest,
    AskResponse,
    DeleteDocumentResponse,
    DocumentListItem,
    DocumentListResponse,
    DocumentUploadResponse,
    MultiAskRequest,
    MultiAskResponse,
    MultiSummarizeRequest,
    MultiSummarizeResponse,
    SummarizeRequest,
    SummarizeResponse,
    UsageStatsResponse,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.llm.factory import create_llm_client
from app.services.documents import ingestor, storage
from app.services.documents.qa import DocumentQA
from app.services.documents.summarize import DocumentSummarizer

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# Supported file extensions
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}


def _get_document_content(document_id: str) -> str:
    """Get and extract document content.

    Args:
        document_id: The document ID

    Returns:
        Extracted text content

    Raises:
        DocumentNotFoundError: If document is not found
        HTTPException: If text extraction fails
    """
    file_path = storage.get_document_path(document_id)
    if not file_path:
        raise DocumentNotFoundError(document_id)

    metadata = storage.get_document_metadata(document_id)
    if not metadata:
        raise DocumentNotFoundError(document_id)

    try:
        return ingestor.extract_text(file_path, metadata.file_type)
    except Exception as e:
        logger.error(f"Error extracting text from {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error extracting text",
        )


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    """Upload a document.

    Args:
        file: The uploaded file

    Returns:
        Document upload response with document_id

    Raises:
        HTTPException: If file type is not supported
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    # Get file extension
    file_ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""

    if file_ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(file_ext)

    # Read file content with size limit
    max_size = settings.max_upload_size_mb * 1024 * 1024
    content = await file.read(max_size + 1)

    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB",
        )

    # Save document
    document_id = storage.save_document(
        filename=file.filename,
        content=content,
        file_type=file_ext,
    )

    logger.info(f"Uploaded document: {document_id} ({file.filename})")

    return DocumentUploadResponse(
        document_id=document_id,
        filename=file.filename,
        message="Document uploaded successfully",
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents() -> DocumentListResponse:
    """List all documents.

    Returns:
        List of documents with metadata
    """
    documents = storage.list_documents()

    items = [
        DocumentListItem(
            document_id=doc.document_id,
            filename=doc.filename,
            file_type=doc.file_type,
            file_size=doc.file_size,
            upload_time=doc.upload_time,
        )
        for doc in documents
    ]

    return DocumentListResponse(documents=items, count=len(items))


@router.get("/stats", response_model=UsageStatsResponse)
async def usage_stats() -> UsageStatsResponse:
    """Return document count and total storage used."""
    documents = storage.list_documents()
    total_bytes = sum(d.file_size for d in documents)
    file_types: dict[str, int] = {}
    for d in documents:
        file_types[d.file_type] = file_types.get(d.file_type, 0) + 1
    return UsageStatsResponse(
        document_count=len(documents),
        total_size_bytes=total_bytes,
        total_size_mb=round(total_bytes / (1024 * 1024), 3),
        file_types=file_types,
    )


def _get_multi_content(document_ids: list[str]) -> str:
    """Concatenate content from multiple documents with separators."""
    if not document_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one document_id is required",
        )
    parts = []
    for doc_id in document_ids:
        parts.append(f"[Document: {doc_id}]\n{_get_document_content(doc_id)}")
    return "\n\n---\n\n".join(parts)


@router.post("/multi/summarize", response_model=MultiSummarizeResponse)
async def multi_summarize(request: MultiSummarizeRequest) -> MultiSummarizeResponse:
    """Summarize multiple documents together.

    Concatenates all document contents and produces a single summary.
    """
    content = _get_multi_content(request.document_ids)

    async with create_llm_client() as llm_client:
        summarizer = DocumentSummarizer(llm_client)
        try:
            summary = await summarizer.summarize(
                content=content,
                max_length=request.max_length,
                style=request.style,
            )
        except Exception as e:
            logger.error(f"Error summarizing multi-document set: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate summary",
            )

    return MultiSummarizeResponse(document_ids=request.document_ids, summary=summary)


@router.post("/multi/ask", response_model=MultiAskResponse)
async def multi_ask(request: MultiAskRequest) -> MultiAskResponse:
    """Ask a question across multiple documents.

    Concatenates all document contents and answers the question in context.
    """
    content = _get_multi_content(request.document_ids)

    async with create_llm_client() as llm_client:
        qa = DocumentQA(llm_client)
        try:
            answer = await qa.answer_question(content=content, question=request.question)
        except Exception as e:
            logger.error(f"Error answering multi-document question: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate answer",
            )

    return MultiAskResponse(
        document_ids=request.document_ids,
        question=request.question,
        answer=answer,
    )


@router.get("/{document_id}", response_model=DocumentListItem)
async def get_document(document_id: str) -> DocumentListItem:
    """Get metadata for a single document by ID."""
    metadata = storage.get_document_metadata(document_id)
    if not metadata:
        raise DocumentNotFoundError(document_id)
    return DocumentListItem(
        document_id=metadata.document_id,
        filename=metadata.filename,
        file_type=metadata.file_type,
        file_size=metadata.file_size,
        upload_time=metadata.upload_time,
    )


@router.delete("/{document_id}", response_model=DeleteDocumentResponse)
async def delete_document(document_id: str) -> DeleteDocumentResponse:
    """Delete a document by ID."""
    deleted = storage.delete_document(document_id)
    if not deleted:
        raise DocumentNotFoundError(document_id)
    logger.info(f"Deleted document: {document_id}")
    return DeleteDocumentResponse(document_id=document_id, message="Document deleted")


@router.post("/{document_id}/summarize", response_model=SummarizeResponse)
async def summarize_document(
    document_id: str,
    request: SummarizeRequest = SummarizeRequest(),
) -> SummarizeResponse:
    """Summarize a document.

    Args:
        document_id: The document ID
        request: Summarization parameters

    Returns:
        Document summary

    Raises:
        HTTPException: If document is not found
    """
    content = _get_document_content(document_id)

    async with create_llm_client() as llm_client:
        summarizer = DocumentSummarizer(llm_client)
        try:
            summary = await summarizer.summarize(
                content=content,
                max_length=request.max_length,
                style=request.style,
            )
        except Exception as e:
            logger.error(f"Error summarizing document {document_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate summary",
            )

    return SummarizeResponse(document_id=document_id, summary=summary)


@router.post("/{document_id}/ask", response_model=AskResponse)
async def ask_question(document_id: str, request: AskRequest) -> AskResponse:
    """Ask a question about a document.

    Args:
        document_id: The document ID
        request: Question request

    Returns:
        Answer to the question

    Raises:
        HTTPException: If document is not found
    """
    content = _get_document_content(document_id)

    async with create_llm_client() as llm_client:
        qa = DocumentQA(llm_client)
        try:
            answer = await qa.answer_question(content=content, question=request.question)
        except Exception as e:
            logger.error(f"Error answering question for document {document_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate answer",
            )

    return AskResponse(document_id=document_id, question=request.question, answer=answer)


def _sse_event(data: str) -> str:
    """Format a string as an SSE data event."""
    return f"data: {data}\n\n"


@router.post("/{document_id}/summarize/stream")
async def summarize_document_stream(
    document_id: str,
    request: SummarizeRequest = SummarizeRequest(),
) -> StreamingResponse:
    """Stream summarization of a document as Server-Sent Events.

    Each chunk is emitted as: data: <text>\\n\\n
    A final 'data: [DONE]\\n\\n' event signals completion.
    """
    content = _get_document_content(document_id)

    async def generate() -> AsyncIterator[str]:
        async with create_llm_client() as llm_client:
            summarizer = DocumentSummarizer(llm_client)
            try:
                async for chunk in summarizer.summarize_stream(
                    content=content,
                    max_length=request.max_length,
                    style=request.style,
                ):
                    yield _sse_event(chunk)
            except Exception as e:
                logger.error(f"Error streaming summarization for {document_id}: {e}")
                yield _sse_event("[ERROR]")
        yield _sse_event("[DONE]")

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/{document_id}/ask/stream")
async def ask_question_stream(
    document_id: str,
    request: AskRequest,
) -> StreamingResponse:
    """Stream an answer to a question as Server-Sent Events.

    Each chunk is emitted as: data: <text>\\n\\n
    A final 'data: [DONE]\\n\\n' event signals completion.
    """
    content = _get_document_content(document_id)

    async def generate() -> AsyncIterator[str]:
        async with create_llm_client() as llm_client:
            qa = DocumentQA(llm_client)
            try:
                async for chunk in qa.answer_question_stream(
                    content=content, question=request.question
                ):
                    yield _sse_event(chunk)
            except Exception as e:
                logger.error(f"Error streaming Q&A for {document_id}: {e}")
                yield _sse_event("[ERROR]")
        yield _sse_event("[DONE]")

    return StreamingResponse(generate(), media_type="text/event-stream")
