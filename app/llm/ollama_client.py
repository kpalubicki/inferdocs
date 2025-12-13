"""Ollama LLM client implementation."""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class OllamaClient:
    """Client for Ollama LLM backend."""

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        """Initialize Ollama client.

        Args:
            base_url: Base URL for Ollama API
            model: Model name to use
        """
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.resolved_model
        self.client = httpx.AsyncClient(timeout=300.0)

    async def generate(self, prompt: str, **params: Any) -> str:
        """Generate a completion using Ollama.

        Args:
            prompt: The input prompt
            **params: Additional parameters

        Returns:
            The generated text
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            **params,
        }

        logger.info(f"Sending request to Ollama: {url}")
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise

    async def stream(self, prompt: str, **params: Any) -> AsyncIterator[str]:
        """Stream a completion using Ollama.

        Args:
            prompt: The input prompt
            **params: Additional parameters

        Yields:
            Chunks of generated text
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            **params,
        }

        logger.info(f"Streaming from Ollama: {url}")
        try:
            async with self.client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]
                        except json.JSONDecodeError:
                            continue
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama streaming HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            raise

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
