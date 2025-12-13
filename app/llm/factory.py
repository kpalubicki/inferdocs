"""Factory for creating LLM clients."""

from typing import Literal

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.base import LLMClient
from app.llm.mock_client import MockClient
from app.llm.ollama_client import OllamaClient
from app.llm.vllm_client import VLLMClient

logger = get_logger(__name__)


def create_llm_client(
    backend: Literal["ollama", "vllm", "mock"] | None = None,
    model: str | None = None,
) -> LLMClient:
    """Create an LLM client based on the backend type.

    Args:
        backend: The backend type (ollama, vllm, or mock)
        model: Optional model name override

    Returns:
        An LLM client instance

    Raises:
        ValueError: If the backend type is invalid
    """
    backend = backend or settings.llm_backend
    model = model or settings.resolved_model

    logger.info(f"Creating LLM client: backend={backend}, model={model}")

    if backend == "ollama":
        return OllamaClient(model=model)  # type: ignore[return-value]
    elif backend == "vllm":
        return VLLMClient(model=model)  # type: ignore[return-value]
    elif backend == "mock":
        return MockClient(model=model)  # type: ignore[return-value]
    else:
        raise ValueError(f"Invalid LLM backend: {backend}")
