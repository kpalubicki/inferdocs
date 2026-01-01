"""Unit tests for document storage - pure logic."""

import tempfile
from pathlib import Path

from app.services.documents.storage import DocumentMetadata, DocumentStorage


class TestDocumentMetadata:
    """Test DocumentMetadata logic."""

    def test_to_dict_conversion(self) -> None:
        """Test converting metadata to dictionary."""
        metadata = DocumentMetadata(
            document_id="test-123",
            filename="test.txt",
            file_type=".txt",
            file_size=1024,
            upload_time="2025-01-01T12:00:00Z"
        )

        result = metadata.to_dict()

        assert result["document_id"] == "test-123"
        assert result["filename"] == "test.txt"
        assert result["file_type"] == ".txt"
        assert result["file_size"] == 1024
        assert result["upload_time"] == "2025-01-01T12:00:00Z"


class TestDocumentStorage:
    """Test DocumentStorage logic."""

    def test_save_document_creates_file(self) -> None:
        """Test that save_document creates a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = DocumentStorage()
            storage.documents_dir = Path(tmpdir)
            storage.metadata_file = Path(tmpdir) / "metadata.json"

            content = b"Test content"
            doc_id = storage.save_document("test.txt", content, ".txt")

            # Check file was created
            assert doc_id is not None
            file_path = storage.documents_dir / f"{doc_id}.txt"
            assert file_path.exists()
            assert file_path.read_bytes() == content

    def test_save_document_stores_metadata(self) -> None:
        """Test that save_document stores metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = DocumentStorage()
            storage.documents_dir = Path(tmpdir)
            storage.metadata_file = Path(tmpdir) / "metadata.json"

            doc_id = storage.save_document("test.txt", b"Content", ".txt")

            metadata = storage.get_document_metadata(doc_id)
            assert metadata is not None
            assert metadata.filename == "test.txt"
            assert metadata.file_type == ".txt"
            assert metadata.file_size == 7  # len(b"Content")

    def test_list_documents_returns_all(self) -> None:
        """Test that list_documents returns all stored documents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = DocumentStorage()
            storage.documents_dir = Path(tmpdir)
            storage.metadata_file = Path(tmpdir) / "metadata.json"
            storage.metadata = {}  # Clear any existing metadata

            # Add two documents
            doc1 = storage.save_document("test1.txt", b"Content1", ".txt")
            doc2 = storage.save_document("test2.md", b"Content2", ".md")

            documents = storage.list_documents()

            assert len(documents) == 2
            filenames = [doc.filename for doc in documents]
            assert "test1.txt" in filenames
            assert "test2.md" in filenames

    def test_delete_document_removes_file_and_metadata(self) -> None:
        """Test that delete_document removes both file and metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = DocumentStorage()
            storage.documents_dir = Path(tmpdir)
            storage.metadata_file = Path(tmpdir) / "metadata.json"

            doc_id = storage.save_document("test.txt", b"Content", ".txt")
            file_path = storage.get_document_path(doc_id)

            # Delete
            result = storage.delete_document(doc_id)

            assert result is True
            assert not file_path.exists() if file_path else True
            assert storage.get_document_metadata(doc_id) is None

    def test_delete_nonexistent_document_returns_false(self) -> None:
        """Test that deleting nonexistent document returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = DocumentStorage()
            storage.documents_dir = Path(tmpdir)
            storage.metadata_file = Path(tmpdir) / "metadata.json"

            result = storage.delete_document("nonexistent-id")

            assert result is False
