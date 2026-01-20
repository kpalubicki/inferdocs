"""Mock LLM client for testing."""

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class MockClient:
    """Mock LLM client for testing."""

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        """Initialize mock client.

        Args:
            base_url: Ignored for mock
            model: Model name (used in response)
        """
        self.model = model or "mock-model"

    async def __aenter__(self) -> "MockClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def generate(self, prompt: str, **params: Any) -> str:
        """Generate a mock completion.

        Args:
            prompt: The input prompt
            **params: Additional parameters

        Returns:
            Mock generated text
        """
        logger.info(f"Mock client generating response for prompt: {prompt[:50]}...")
        await asyncio.sleep(0.1)  # Simulate processing time
        return f"Mock response to: {prompt} (model: {self.model})"

    async def stream(self, prompt: str, **params: Any) -> AsyncIterator[str]:
        """Stream a mock completion.

        Args:
            prompt: The input prompt
            **params: Additional parameters

        Yields:
            Chunks of mock generated text
        """
        logger.info(f"Mock client streaming response for prompt: {prompt[:50]}...")
        response = f"Mock streaming response to: {prompt} (model: {self.model})"
        words = response.split()

        for word in words:
            await asyncio.sleep(0.05)
            yield word + " "

    async def close(self) -> None:
        """Close the client (no-op for mock)."""
        pass
