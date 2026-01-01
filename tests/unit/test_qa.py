"""Unit tests for document Q&A - pure logic."""

from app.llm.mock_client import MockClient
from app.services.documents.qa import DocumentQA


class TestDocumentQA:
    """Test DocumentQA prompt building logic."""

    def test_build_qa_prompt_basic(self) -> None:
        """Test basic Q&A prompt building."""
        client = MockClient()
        qa = DocumentQA(client)

        prompt = qa._build_qa_prompt("Document content", "What is this?")

        assert "Document content" in prompt
        assert "What is this?" in prompt
        assert "question" in prompt.lower()

    def test_build_qa_prompt_structure(self) -> None:
        """Test that prompt has proper structure."""
        client = MockClient()
        qa = DocumentQA(client)

        prompt = qa._build_qa_prompt("Content here", "Question here")

        # Should have document content section
        assert "Document content:" in prompt or "document" in prompt.lower()
        # Should have question section
        assert "Question:" in prompt
        # Should have answer section
        assert "Answer:" in prompt

    def test_build_qa_prompt_preserves_content(self) -> None:
        """Test that prompt preserves all content."""
        client = MockClient()
        qa = DocumentQA(client)

        content = "This is important content with special chars: ąćę"
        question = "What does it say?"

        prompt = qa._build_qa_prompt(content, question)

        assert content in prompt
        assert question in prompt
