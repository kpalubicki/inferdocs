"""Conversation history storage — persists Q&A pairs per document."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ConversationEntry:
    def __init__(self, timestamp: str, question: str, answer: str) -> None:
        self.timestamp = timestamp
        self.question = question
        self.answer = answer

    def to_dict(self) -> dict:
        return {"timestamp": self.timestamp, "question": self.question, "answer": self.answer}


class ConversationStore:
    """Persists per-document Q&A history as JSON files in the documents directory."""

    def _history_path(self, document_id: str) -> Path:
        return Path(settings.documents_dir) / f"{document_id}.history.json"

    def load(self, document_id: str) -> list[ConversationEntry]:
        path = self._history_path(document_id)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return [ConversationEntry(**e) for e in data]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.error(f"Failed to load history for {document_id}: {exc}")
            return []

    def append(self, document_id: str, question: str, answer: str) -> None:
        entries = self.load(document_id)
        entries.append(
            ConversationEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                question=question,
                answer=answer,
            )
        )
        path = self._history_path(document_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps([e.to_dict() for e in entries], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def clear(self, document_id: str) -> bool:
        """Delete history file. Returns True if it existed."""
        path = self._history_path(document_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def to_markdown(self, document_id: str, filename: str) -> str:
        entries = self.load(document_id)
        lines = [f"# Conversation history — {filename}\n"]
        if not entries:
            lines.append("_No conversations recorded._")
            return "\n".join(lines)
        for i, e in enumerate(entries, start=1):
            lines.append(f"## Q{i} — {e.timestamp}")
            lines.append(f"**Question:** {e.question}\n")
            lines.append(f"**Answer:**\n\n{e.answer}\n")
        return "\n".join(lines)


conversation_store = ConversationStore()
