"""Document management endpoints."""

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.api.errors import DocumentNotFoundError, UnsupportedFileTypeError
from app.api.schemas import (
    AskRequest,
    AskResponse,
    DocumentListItem,
    DocumentListResponse,
    DocumentUploadResponse,
    SummarizeRequest,
    SummarizeResponse,
)
from app.core.logging import get_logger
from app.llm.factory import create_llm_client
from app.services.documents import ingestor, storage
from app.services.documents.qa import DocumentQA
from app.services.documents.summarize import DocumentSummarizer

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# Supported file extensions
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}


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

    # Read file content
    content = await file.read()

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
    # Get document
    file_path = storage.get_document_path(document_id)
    if not file_path:
        raise DocumentNotFoundError(document_id)

    metadata = storage.get_document_metadata(document_id)
    if not metadata:
        raise DocumentNotFoundError(document_id)

    # Extract text
    try:
        content = ingestor.extract_text(file_path, metadata.file_type)
    except Exception as e:
        logger.error(f"Error extracting text from {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting text: {str(e)}",
        )

    # Create LLM client and summarizer
    llm_client = create_llm_client()
    summarizer = DocumentSummarizer(llm_client)

    # Generate summary
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
            detail=f"Error generating summary: {str(e)}",
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
    # Get document
    file_path = storage.get_document_path(document_id)
    if not file_path:
        raise DocumentNotFoundError(document_id)

    metadata = storage.get_document_metadata(document_id)
    if not metadata:
        raise DocumentNotFoundError(document_id)

    # Extract text
    try:
        content = ingestor.extract_text(file_path, metadata.file_type)
    except Exception as e:
        logger.error(f"Error extracting text from {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting text: {str(e)}",
        )

    # Create LLM client and QA
    llm_client = create_llm_client()
    qa = DocumentQA(llm_client)

    # Answer question
    try:
        answer = await qa.answer_question(content=content, question=request.question)
    except Exception as e:
        logger.error(f"Error answering question for document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating answer: {str(e)}",
        )

    return AskResponse(document_id=document_id, question=request.question, answer=answer)
