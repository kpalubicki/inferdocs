"""Unit tests for LLM clients - pure logic without network calls."""

import pytest

from app.llm.mock_client import MockClient


class TestMockClient:
    """Test MockClient logic."""

    @pytest.mark.asyncio
    async def test_generate_returns_mock_response(self) -> None:
        """Test that generate returns a mock response with the prompt."""
        client = MockClient(model="test-model")
        prompt = "Test prompt"

        result = await client.generate(prompt)

        assert "Mock response" in result
        assert prompt in result
        assert "test-model" in result

    @pytest.mark.asyncio
    async def test_generate_with_custom_model(self) -> None:
        """Test that generate uses custom model name."""
        client = MockClient(model="custom-model")
        prompt = "Hello"

        result = await client.generate(prompt)

        assert "custom-model" in result

    @pytest.mark.asyncio
    async def test_stream_yields_words(self) -> None:
        """Test that stream yields individual words."""
        client = MockClient(model="test-model")
        prompt = "Test"

        chunks = []
        async for chunk in client.stream(prompt):
            chunks.append(chunk)

        # Should get multiple chunks (words)
        assert len(chunks) > 1
        # Reconstruct the full message
        full_message = "".join(chunks)
        assert "Mock streaming response" in full_message
        assert prompt in full_message

    @pytest.mark.asyncio
    async def test_close_is_noop(self) -> None:
        """Test that close doesn't raise errors."""
        client = MockClient()
        await client.close()  # Should not raise
