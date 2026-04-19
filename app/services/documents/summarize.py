"""Document summarization service."""

from collections.abc import AsyncIterator

from app.core.logging import get_logger
from app.llm.base import LLMClient

logger = get_logger(__name__)


class DocumentSummarizer:
    """Handles document summarization using LLM."""

    def __init__(self, llm_client: LLMClient) -> None:
        """Initialize summarizer with an LLM client.

        Args:
            llm_client: The LLM client to use for summarization
        """
        self.llm_client = llm_client

    async def summarize(
        self,
        content: str,
        max_length: int | None = None,
        style: str | None = None,
        language: str | None = None,
    ) -> str:
        """Summarize document content."""
        prompt = self._build_summarization_prompt(content, max_length, style, language)
        logger.info(f"Summarizing document ({len(content)} chars)")

        try:
            summary = await self.llm_client.generate(prompt)
            logger.info(f"Generated summary ({len(summary)} chars)")
            return summary
        except Exception as e:
            logger.error(f"Error during summarization: {e}")
            raise

    async def summarize_stream(
        self,
        content: str,
        max_length: int | None = None,
        style: str | None = None,
        language: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream summarization of document content."""
        prompt = self._build_summarization_prompt(content, max_length, style, language)
        logger.info(f"Streaming summarization ({len(content)} chars)")
        try:
            async for chunk in await self.llm_client.stream(prompt):
                yield chunk
        except Exception as e:
            logger.error(f"Error during streaming summarization: {e}")
            raise

    def _build_summarization_prompt(
        self,
        content: str,
        max_length: int | None = None,
        style: str | None = None,
        language: str | None = None,
    ) -> str:
        """Build the summarization prompt."""
        lang_instruction = f" Respond in {language}." if language else ""
        prompt_parts = [f"Please summarize the following document.{lang_instruction}"]

        if style:
            prompt_parts.append(f"Style: {style}")

        if max_length:
            prompt_parts.append(f"Maximum length: approximately {max_length} words")

        prompt_parts.append("\nDocument content:")
        prompt_parts.append(content)
        prompt_parts.append("\nSummary:")

        return "\n".join(prompt_parts)
