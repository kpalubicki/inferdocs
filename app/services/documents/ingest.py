"""Document ingestion utilities."""

from pathlib import Path

from pypdf import PdfReader

from app.core.logging import get_logger

logger = get_logger(__name__)


class DocumentIngestor:
    """Handles document content extraction."""

    @staticmethod
    def extract_text(file_path: Path, file_type: str) -> str:
        """Extract text content from a document.

        Args:
            file_path: Path to the document
            file_type: File type extension (e.g., '.txt', '.md', '.pdf')

        Returns:
            Extracted text content

        Raises:
            ValueError: If file type is not supported
        """
        if file_type in [".txt", ".md"]:
            return DocumentIngestor._extract_text_file(file_path)
        elif file_type == ".pdf":
            return DocumentIngestor._extract_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    @staticmethod
    def _extract_text_file(file_path: Path) -> str:
        """Extract text from a text/markdown file.

        Args:
            file_path: Path to the text file

        Returns:
            File content as string
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            logger.info(f"Extracted {len(content)} characters from {file_path.name}")
            return content
        except Exception as e:
            logger.error(f"Error reading text file {file_path}: {e}")
            raise

    @staticmethod
    def _extract_pdf(file_path: Path) -> str:
        """Extract text from a PDF file.

        Args:
            file_path: Path to the PDF file

        Returns:
            Extracted text content
        """
        try:
            reader = PdfReader(file_path)
            text_parts = []

            for page_num, page in enumerate(reader.pages, 1):
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            content = "\n\n".join(text_parts)
            logger.info(
                f"Extracted {len(content)} characters from {len(reader.pages)} "
                f"pages in {file_path.name}"
            )
            return content
        except Exception as e:
            logger.error(f"Error reading PDF file {file_path}: {e}")
            raise


# Global ingestor instance
ingestor = DocumentIngestor()
