"""vLLM client implementation using OpenAI-compatible API."""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class VLLMClient:
    """Client for vLLM backend using OpenAI-compatible API."""

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = base_url or settings.vllm_base_url
        self.model = model or settings.resolved_model
        self.client = httpx.AsyncClient(timeout=300.0)

    async def __aenter__(self) -> "VLLMClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def generate(self, prompt: str, **params: Any) -> str:
        """Generate a completion using vLLM.

        Args:
            prompt: The input prompt
            **params: Additional parameters

        Returns:
            The generated text
        """
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            **params,
        }

        logger.info(f"Sending request to vLLM: {url}")
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error(f"vLLM HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"vLLM error: {e}")
            raise

    async def stream(self, prompt: str, **params: Any) -> AsyncIterator[str]:
        """Stream a completion using vLLM.

        Args:
            prompt: The input prompt
            **params: Additional parameters

        Yields:
            Chunks of generated text
        """
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            **params,
        }

        logger.info(f"Streaming from vLLM: {url}")
        try:
            async with self.client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if (
                                "choices" in data
                                and len(data["choices"]) > 0
                                and "delta" in data["choices"][0]
                                and "content" in data["choices"][0]["delta"]
                            ):
                                yield data["choices"][0]["delta"]["content"]
                        except json.JSONDecodeError:
                            continue
        except httpx.HTTPStatusError as e:
            logger.error(f"vLLM streaming HTTP error: {e}")
            # Fallback to non-streaming
            result = await self.generate(prompt, **params)
            yield result
        except Exception as e:
            logger.error(f"vLLM streaming error: {e}")
            raise

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
