"""Tests for document summarization with mock backend."""

from pathlib import Path

from fastapi.testclient import TestClient


def test_summarize_document(client: TestClient, sample_txt_file: Path) -> None:
    """Test summarizing a document with mock backend."""
    # Upload a document
    with open(sample_txt_file, "rb") as f:
        upload_response = client.post(
            "/documents",
            files={"file": ("test.txt", f, "text/plain")},
        )
    document_id = upload_response.json()["document_id"]

    # Summarize the document
    response = client.post(f"/documents/{document_id}/summarize", json={})

    assert response.status_code == 200
    data = response.json()

    assert data["document_id"] == document_id
    assert "summary" in data
    assert len(data["summary"]) > 0
    assert "Mock response" in data["summary"]


def test_summarize_with_max_length(client: TestClient, sample_txt_file: Path) -> None:
    """Test summarization with max_length parameter."""
    # Upload a document
    with open(sample_txt_file, "rb") as f:
        upload_response = client.post(
            "/documents",
            files={"file": ("test.txt", f, "text/plain")},
        )
    document_id = upload_response.json()["document_id"]

    # Summarize with max_length
    response = client.post(
        f"/documents/{document_id}/summarize",
        json={"max_length": 50},
    )

    assert response.status_code == 200
    data = response.json()
    assert "summary" in data


def test_summarize_with_style(client: TestClient, sample_txt_file: Path) -> None:
    """Test summarization with style parameter."""
    # Upload a document
    with open(sample_txt_file, "rb") as f:
        upload_response = client.post(
            "/documents",
            files={"file": ("test.txt", f, "text/plain")},
        )
    document_id = upload_response.json()["document_id"]

    # Summarize with style
    response = client.post(
        f"/documents/{document_id}/summarize",
        json={"style": "brief"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "summary" in data


def test_summarize_nonexistent_document(client: TestClient) -> None:
    """Test summarizing a document that doesn't exist."""
    response = client.post("/documents/nonexistent-id/summarize", json={})

    assert response.status_code == 404
    data = response.json()
    assert "error" in data
