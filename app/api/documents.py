"""Document management endpoints."""

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import Response, StreamingResponse

from app.api.errors import DocumentNotFoundError, UnsupportedFileTypeError
from app.api.schemas import (
    AskRequest,
    AskResponse,
    ConversationEntrySchema,
    ConversationHistoryResponse,
    DeleteDocumentResponse,
    DocumentListItem,
    DocumentListResponse,
    DocumentUploadResponse,
    MultiAskRequest,
    MultiAskResponse,
    MultiSummarizeRequest,
    MultiSummarizeResponse,
    SimilarDocumentItem,
    SimilarDocumentsResponse,
    SummarizeRequest,
    SummarizeResponse,
    TagsRequest,
    UsageStatsResponse,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.llm.factory import create_llm_client
from app.services.documents import ingestor, storage
from app.services.documents.similarity import find_similar
from app.services.documents.history import conversation_store
from app.services.documents.language import detect_language
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

    # Detect language from extracted text
    try:
        temp_path = storage.documents_dir / f"_tmp_lang{file_ext}"
        temp_path.write_bytes(content)
        text_sample = ingestor.extract_text(temp_path, file_ext)
        temp_path.unlink(missing_ok=True)
        detected_language = detect_language(text_sample)
    except Exception:
        detected_language = None

    # Save document
    document_id = storage.save_document(
        filename=file.filename,
        content=content,
        file_type=file_ext,
        language=detected_language,
    )

    logger.info(f"Uploaded document: {document_id} ({file.filename})")

    return DocumentUploadResponse(
        document_id=document_id,
        filename=file.filename,
        message="Document uploaded successfully",
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(tag: str | None = None) -> DocumentListResponse:
    """List all documents, optionally filtered by tag."""
    documents = storage.list_documents(tag=tag)

    items = [
        DocumentListItem(
            document_id=doc.document_id,
            filename=doc.filename,
            file_type=doc.file_type,
            file_size=doc.file_size,
            upload_time=doc.upload_time,
            language=doc.language,
            tags=doc.tags,
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
        language=metadata.language,
        tags=metadata.tags,
    )


@router.delete("/{document_id}", response_model=DeleteDocumentResponse)
async def delete_document(document_id: str) -> DeleteDocumentResponse:
    """Delete a document by ID."""
    deleted = storage.delete_document(document_id)
    if not deleted:
        raise DocumentNotFoundError(document_id)
    conversation_store.clear(document_id)
    logger.info(f"Deleted document: {document_id}")
    return DeleteDocumentResponse(document_id=document_id, message="Document deleted")


@router.put("/{document_id}/tags", response_model=DocumentListItem)
async def set_document_tags(document_id: str, request: TagsRequest) -> DocumentListItem:
    """Set tags for a document, replacing existing ones."""
    updated = storage.set_tags(document_id, request.tags)
    if not updated:
        raise DocumentNotFoundError(document_id)
    metadata = storage.get_document_metadata(document_id)
    return DocumentListItem(
        document_id=metadata.document_id,  # type: ignore[union-attr]
        filename=metadata.filename,  # type: ignore[union-attr]
        file_type=metadata.file_type,  # type: ignore[union-attr]
        file_size=metadata.file_size,  # type: ignore[union-attr]
        upload_time=metadata.upload_time,  # type: ignore[union-attr]
        language=metadata.language,  # type: ignore[union-attr]
        tags=metadata.tags,  # type: ignore[union-attr]
    )


@router.get("/{document_id}/similar", response_model=SimilarDocumentsResponse)
async def similar_documents(document_id: str, top: int = 5) -> SimilarDocumentsResponse:
    """Find documents most similar to the given one using TF-IDF cosine similarity.

    Returns up to `top` results (default 5), ordered by similarity score descending.
    Scores range from 0 (no overlap) to 1 (identical content).
    """
    if top < 1 or top > 20:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="top must be between 1 and 20",
        )

    target_content = _get_document_content(document_id)

    all_docs = storage.list_documents()
    candidates: list[tuple[str, str]] = []
    for doc in all_docs:
        if doc.document_id == document_id:
            continue
        doc_path = storage.get_document_path(doc.document_id)
        if not doc_path:
            continue
        try:
            text = ingestor.extract_text(doc_path, doc.file_type)
            if text.strip():
                candidates.append((doc.document_id, text))
        except Exception:
            continue

    similar = find_similar(target_content, candidates, top_n=top)

    results: list[SimilarDocumentItem] = []
    for doc_id, score in similar:
        meta = storage.get_document_metadata(doc_id)
        if meta:
            results.append(SimilarDocumentItem(
                document_id=doc_id,
                filename=meta.filename,
                score=score,
            ))

    return SimilarDocumentsResponse(
        document_id=document_id,
        top_n=top,
        results=results,
    )


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
    metadata = storage.get_document_metadata(document_id)
    language = metadata.language if metadata else None

    async with create_llm_client() as llm_client:
        summarizer = DocumentSummarizer(llm_client)
        try:
            summary = await summarizer.summarize(
                content=content,
                max_length=request.max_length,
                style=request.style,
                language=language,
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
    metadata = storage.get_document_metadata(document_id)
    language = metadata.language if metadata else None

    async with create_llm_client() as llm_client:
        qa = DocumentQA(llm_client)
        try:
            answer = await qa.answer_question(
                content=content, question=request.question, language=language
            )
        except Exception as e:
            logger.error(f"Error answering question for document {document_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate answer",
            )

    conversation_store.append(document_id, request.question, answer)
    return AskResponse(document_id=document_id, question=request.question, answer=answer)


@router.get("/{document_id}/history", response_model=ConversationHistoryResponse)
async def get_conversation_history(document_id: str) -> ConversationHistoryResponse:
    """Return the recorded Q&A history for a document."""
    metadata = storage.get_document_metadata(document_id)
    if not metadata:
        raise DocumentNotFoundError(document_id)
    entries = conversation_store.load(document_id)
    return ConversationHistoryResponse(
        document_id=document_id,
        filename=metadata.filename,
        count=len(entries),
        entries=[ConversationEntrySchema(**e.to_dict()) for e in entries],
    )


@router.get("/{document_id}/history/export")
async def export_conversation_history(
    document_id: str, format: str = "md"
) -> Response:
    """Download conversation history as Markdown (default) or JSON.

    Use ?format=json for JSON download.
    """
    metadata = storage.get_document_metadata(document_id)
    if not metadata:
        raise DocumentNotFoundError(document_id)

    safe_name = metadata.filename.rsplit(".", 1)[0][:40].replace(" ", "-")

    if format == "json":
        entries = conversation_store.load(document_id)
        content = json.dumps(
            [e.to_dict() for e in entries], indent=2, ensure_ascii=False
        ).encode("utf-8")
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}-history.json"'},
        )

    md = conversation_store.to_markdown(document_id, metadata.filename)
    return Response(
        content=md.encode("utf-8"),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}-history.md"'},
    )


@router.delete("/{document_id}/history", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def clear_conversation_history(document_id: str) -> None:
    """Delete all recorded Q&A history for a document."""
    metadata = storage.get_document_metadata(document_id)
    if not metadata:
        raise DocumentNotFoundError(document_id)
    conversation_store.clear(document_id)


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
    _meta = storage.get_document_metadata(document_id)
    _language = _meta.language if _meta else None

    async def generate() -> AsyncIterator[str]:
        async with create_llm_client() as llm_client:
            summarizer = DocumentSummarizer(llm_client)
            try:
                async for chunk in summarizer.summarize_stream(
                    content=content,
                    max_length=request.max_length,
                    style=request.style,
                    language=_language,
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
    _meta = storage.get_document_metadata(document_id)
    _language = _meta.language if _meta else None

    async def generate() -> AsyncIterator[str]:
        async with create_llm_client() as llm_client:
            qa = DocumentQA(llm_client)
            try:
                async for chunk in qa.answer_question_stream(
                    content=content, question=request.question, language=_language
                ):
                    yield _sse_event(chunk)
            except Exception as e:
                logger.error(f"Error streaming Q&A for {document_id}: {e}")
                yield _sse_event("[ERROR]")
        yield _sse_event("[DONE]")

    return StreamingResponse(generate(), media_type="text/event-stream")
