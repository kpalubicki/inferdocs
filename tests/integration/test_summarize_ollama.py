"""Integration tests for document summarization with Ollama backend."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Skip these tests if Ollama is not available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.skipif(
        os.getenv("SKIP_INTEGRATION") == "1",
        reason="Integration tests disabled",
    ),
]


@pytest.fixture
def ollama_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Create a test client with Ollama backend."""
    monkeypatch.setenv("LLM_BACKEND", "ollama")
    monkeypatch.setenv("LLM_MODEL", "qwen2.5:3b")

    # Force reload
    from importlib import reload

    from app.core import config
    from app.main import app

    reload(config)

    return TestClient(app)


def test_summarize_with_ollama(ollama_client: TestClient, sample_txt_file: Path) -> None:
    """Test summarization with real Ollama backend."""
    # Upload a document
    with open(sample_txt_file, "rb") as f:
        upload_response = ollama_client.post(
            "/documents",
            files={"file": ("test.txt", f, "text/plain")},
        )

    assert upload_response.status_code == 201
    document_id = upload_response.json()["document_id"]

    # Summarize the document
    response = ollama_client.post(f"/documents/{document_id}/summarize", json={})

    assert response.status_code == 200
    data = response.json()

    assert data["document_id"] == document_id
    assert "summary" in data
    assert len(data["summary"]) > 0
    # Should not contain mock response
    assert "Mock response" not in data["summary"]


def test_ask_with_ollama(ollama_client: TestClient, sample_md_file: Path) -> None:
    """Test Q&A with real Ollama backend."""
    # Upload a document
    with open(sample_md_file, "rb") as f:
        upload_response = ollama_client.post(
            "/documents",
            files={"file": ("test.md", f, "text/markdown")},
        )

    assert upload_response.status_code == 201
    document_id = upload_response.json()["document_id"]

    # Ask a question
    question = "What are the features mentioned in this document?"
    response = ollama_client.post(
        f"/documents/{document_id}/ask",
        json={"question": question},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["document_id"] == document_id
    assert data["question"] == question
    assert "answer" in data
    assert len(data["answer"]) > 0
    # Should not contain mock response
    assert "Mock response" not in data["answer"]
