"""Document storage management."""

import json
import uuid
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class DocumentMetadata:
    """Document metadata."""

    def __init__(
        self,
        document_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        upload_time: str,
    ) -> None:
        """Initialize document metadata."""
        self.document_id = document_id
        self.filename = filename
        self.file_type = file_type
        self.file_size = file_size
        self.upload_time = upload_time

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "upload_time": self.upload_time,
        }


class DocumentStorage:
    """Manages document storage and metadata."""

    def __init__(self) -> None:
        """Initialize document storage."""
        self.documents_dir = Path(settings.documents_dir)
        self.metadata_file = Path(settings.metadata_file)
        self.metadata: dict[str, DocumentMetadata] = {}

        # Create directories if they don't exist
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing metadata
        self._load_metadata()

    def _load_metadata(self) -> None:
        """Load metadata from file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, encoding="utf-8") as f:
                    data = json.load(f)
                    for doc_id, meta in data.items():
                        self.metadata[doc_id] = DocumentMetadata(
                            document_id=meta["document_id"],
                            filename=meta["filename"],
                            file_type=meta["file_type"],
                            file_size=meta["file_size"],
                            upload_time=meta["upload_time"],
                        )
                logger.info(f"Loaded {len(self.metadata)} documents from metadata")
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")
                self.metadata = {}

    def _save_metadata(self) -> None:
        """Save metadata to file."""
        try:
            data = {doc_id: meta.to_dict() for doc_id, meta in self.metadata.items()}
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved metadata for {len(self.metadata)} documents")
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")

    def save_document(self, filename: str, content: bytes, file_type: str) -> str:
        """Save a document and return its ID.

        Args:
            filename: Original filename
            content: File content
            file_type: File type (extension)

        Returns:
            Document ID
        """
        import datetime

        document_id = str(uuid.uuid4())
        file_path = self.documents_dir / f"{document_id}{file_type}"

        # Save file
        with open(file_path, "wb") as f:
            f.write(content)

        # Save metadata
        metadata = DocumentMetadata(
            document_id=document_id,
            filename=filename,
            file_type=file_type,
            file_size=len(content),
            upload_time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )
        self.metadata[document_id] = metadata
        self._save_metadata()

        logger.info(f"Saved document {document_id}: {filename}")
        return document_id

    def get_document_path(self, document_id: str) -> Path | None:
        """Get the file path for a document.

        Args:
            document_id: Document ID

        Returns:
            Path to the document file, or None if not found
        """
        metadata = self.metadata.get(document_id)
        if not metadata:
            return None

        file_path = self.documents_dir / f"{document_id}{metadata.file_type}"
        if file_path.exists():
            return file_path
        return None

    def get_document_metadata(self, document_id: str) -> DocumentMetadata | None:
        """Get metadata for a document.

        Args:
            document_id: Document ID

        Returns:
            Document metadata, or None if not found
        """
        return self.metadata.get(document_id)

    def list_documents(self) -> list[DocumentMetadata]:
        """List all documents.

        Returns:
            List of document metadata
        """
        return list(self.metadata.values())

    def delete_document(self, document_id: str) -> bool:
        """Delete a document.

        Args:
            document_id: Document ID

        Returns:
            True if deleted, False if not found
        """
        file_path = self.get_document_path(document_id)
        if file_path and file_path.exists():
            file_path.unlink()

        if document_id in self.metadata:
            del self.metadata[document_id]
            self._save_metadata()
            logger.info(f"Deleted document {document_id}")
            return True

        return False


# Global storage instance
storage = DocumentStorage()
