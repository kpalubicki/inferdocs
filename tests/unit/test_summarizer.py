"""Unit tests for document summarizer - pure logic."""

from app.llm.mock_client import MockClient
from app.services.documents.summarize import DocumentSummarizer


class TestDocumentSummarizer:
    """Test DocumentSummarizer prompt building logic."""

    def test_build_summarization_prompt_basic(self) -> None:
        """Test basic prompt building."""
        client = MockClient()
        summarizer = DocumentSummarizer(client)

        prompt = summarizer._build_summarization_prompt("Test content")

        assert "Test content" in prompt
        assert "summarize" in prompt.lower()

    def test_build_summarization_prompt_with_max_length(self) -> None:
        """Test prompt with max_length parameter."""
        client = MockClient()
        summarizer = DocumentSummarizer(client)

        prompt = summarizer._build_summarization_prompt("Content", max_length=100)

        assert "100" in prompt
        assert "words" in prompt.lower()

    def test_build_summarization_prompt_with_style(self) -> None:
        """Test prompt with style parameter."""
        client = MockClient()
        summarizer = DocumentSummarizer(client)

        prompt = summarizer._build_summarization_prompt("Content", style="brief")

        assert "brief" in prompt.lower()

    def test_build_summarization_prompt_with_all_params(self) -> None:
        """Test prompt with all parameters."""
        client = MockClient()
        summarizer = DocumentSummarizer(client)

        prompt = summarizer._build_summarization_prompt(
            "Test content here",
            max_length=50,
            style="detailed"
        )

        assert "Test content here" in prompt
        assert "50" in prompt
        assert "detailed" in prompt.lower()
