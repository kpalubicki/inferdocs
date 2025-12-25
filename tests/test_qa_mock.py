"""Tests for document Q&A with mock backend."""

from pathlib import Path

from fastapi.testclient import TestClient


def test_ask_question(client: TestClient, sample_txt_file: Path) -> None:
    """Test asking a question about a document with mock backend."""
    # Upload a document
    with open(sample_txt_file, "rb") as f:
        upload_response = client.post(
            "/documents",
            files={"file": ("test.txt", f, "text/plain")},
        )
    document_id = upload_response.json()["document_id"]

    # Ask a question
    question = "What is this document about?"
    response = client.post(
        f"/documents/{document_id}/ask",
        json={"question": question},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["document_id"] == document_id
    assert data["question"] == question
    assert "answer" in data
    assert len(data["answer"]) > 0
    assert "Mock response" in data["answer"]


def test_ask_question_empty(client: TestClient, sample_txt_file: Path) -> None:
    """Test asking an empty question."""
    # Upload a document
    with open(sample_txt_file, "rb") as f:
        upload_response = client.post(
            "/documents",
            files={"file": ("test.txt", f, "text/plain")},
        )
    document_id = upload_response.json()["document_id"]

    # Ask empty question (should still work with mock)
    response = client.post(
        f"/documents/{document_id}/ask",
        json={"question": ""},
    )

    # Empty string is still valid for the API
    assert response.status_code == 200


def test_ask_question_nonexistent_document(client: TestClient) -> None:
    """Test asking a question about a document that doesn't exist."""
    response = client.post(
        "/documents/nonexistent-id/ask",
        json={"question": "What is this?"},
    )

    assert response.status_code == 404
    data = response.json()
    assert "error" in data


def test_ask_question_missing_question_field(client: TestClient, sample_txt_file: Path) -> None:
    """Test asking without providing question field."""
    # Upload a document
    with open(sample_txt_file, "rb") as f:
        upload_response = client.post(
            "/documents",
            files={"file": ("test.txt", f, "text/plain")},
        )
    document_id = upload_response.json()["document_id"]

    # Ask without question field
    response = client.post(f"/documents/{document_id}/ask", json={})

    assert response.status_code == 422  # Unprocessable Entity
