"""Base LLM client protocol."""

from collections.abc import AsyncIterator
from typing import Any, Protocol


class LLMClient(Protocol):
    """Protocol for LLM client implementations."""

    async def generate(self, prompt: str, **params: Any) -> str:
        """Generate a completion for the given prompt.

        Args:
            prompt: The input prompt
            **params: Additional parameters for the model

        Returns:
            The generated text
        """
        ...

    async def stream(self, prompt: str, **params: Any) -> AsyncIterator[str]:
        """Stream a completion for the given prompt.

        Args:
            prompt: The input prompt
            **params: Additional parameters for the model

        Yields:
            Chunks of generated text
        """
        ...
