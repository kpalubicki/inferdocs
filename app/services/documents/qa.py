"""Document Q&A service."""

from collections.abc import AsyncIterator

from app.core.logging import get_logger
from app.llm.base import LLMClient

logger = get_logger(__name__)


class DocumentQA:
    """Handles question-answering for documents using LLM."""

    def __init__(self, llm_client: LLMClient) -> None:
        """Initialize QA with an LLM client.

        Args:
            llm_client: The LLM client to use for Q&A
        """
        self.llm_client = llm_client

    async def answer_question(self, content: str, question: str) -> str:
        """Answer a question about document content.

        Args:
            content: The document content
            question: The question to answer

        Returns:
            The answer text
        """
        prompt = self._build_qa_prompt(content, question)
        logger.info(f"Answering question about document ({len(content)} chars)")

        try:
            answer = await self.llm_client.generate(prompt)
            logger.info(f"Generated answer ({len(answer)} chars)")
            return answer
        except Exception as e:
            logger.error(f"Error during Q&A: {e}")
            raise

    async def answer_question_stream(self, content: str, question: str) -> AsyncIterator[str]:
        """Stream an answer to a question about document content."""
        prompt = self._build_qa_prompt(content, question)
        logger.info(f"Streaming Q&A for document ({len(content)} chars)")
        try:
            async for chunk in await self.llm_client.stream(prompt):
                yield chunk
        except Exception as e:
            logger.error(f"Error during streaming Q&A: {e}")
            raise

    def _build_qa_prompt(self, content: str, question: str) -> str:
        """Build the Q&A prompt.

        Args:
            content: The document content
            question: The question

        Returns:
            The formatted prompt
        """
        prompt = f"""Based on the following document, please answer the question.

Document content:
{content}

Question: {question}

Answer:"""
        return prompt
