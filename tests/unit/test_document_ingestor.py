"""Unit tests for document ingestor - pure logic."""

import tempfile
from pathlib import Path

import pytest

from app.services.documents.ingest import DocumentIngestor


class TestDocumentIngestor:
    """Test DocumentIngestor logic."""

    def test_extract_text_from_txt_file(self) -> None:
        """Test extracting text from a .txt file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Hello World\nThis is a test.")
            temp_path = Path(f.name)

        try:
            result = DocumentIngestor.extract_text(temp_path, ".txt")
            assert result == "Hello World\nThis is a test."
        finally:
            temp_path.unlink()

    def test_extract_text_from_md_file(self) -> None:
        """Test extracting text from a .md file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Title\n\nContent here.")
            temp_path = Path(f.name)

        try:
            result = DocumentIngestor.extract_text(temp_path, ".md")
            assert "# Title" in result
            assert "Content here." in result
        finally:
            temp_path.unlink()

    def test_extract_text_unsupported_type_raises_error(self) -> None:
        """Test that unsupported file type raises ValueError."""
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Unsupported file type"):
                DocumentIngestor.extract_text(temp_path, ".xyz")
        finally:
            temp_path.unlink()

    def test_extract_text_preserves_encoding(self) -> None:
        """Test that UTF-8 encoding is preserved."""
        content = "Test with special chars: ąćęłńóśźż"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            result = DocumentIngestor.extract_text(temp_path, ".txt")
            assert result == content
        finally:
            temp_path.unlink()
