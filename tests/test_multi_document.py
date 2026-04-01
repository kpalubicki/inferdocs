"""Tests for multi-document summarize and ask endpoints."""

from pathlib import Path

from fastapi.testclient import TestClient


def _upload(client: TestClient, file_path: Path, name: str) -> str:
    with open(file_path, "rb") as f:
        r = client.post("/documents", files={"file": (name, f, "text/plain")})
    assert r.status_code == 201
    return r.json()["document_id"]


def test_multi_ask_two_documents(client: TestClient, temp_data_dir: Path) -> None:
    doc1 = temp_data_dir / "doc1.txt"
    doc2 = temp_data_dir / "doc2.txt"
    doc1.write_text("Document one is about Python programming.")
    doc2.write_text("Document two is about FastAPI web framework.")

    id1 = _upload(client, doc1, "doc1.txt")
    id2 = _upload(client, doc2, "doc2.txt")

    r = client.post("/documents/multi/ask", json={
        "document_ids": [id1, id2],
        "question": "What are both documents about?",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["document_ids"] == [id1, id2]
    assert data["question"] == "What are both documents about?"
    assert len(data["answer"]) > 0


def test_multi_summarize_two_documents(client: TestClient, temp_data_dir: Path) -> None:
    doc1 = temp_data_dir / "s1.txt"
    doc2 = temp_data_dir / "s2.txt"
    doc1.write_text("First document content.")
    doc2.write_text("Second document content.")

    id1 = _upload(client, doc1, "s1.txt")
    id2 = _upload(client, doc2, "s2.txt")

    r = client.post("/documents/multi/summarize", json={"document_ids": [id1, id2]})
    assert r.status_code == 200
    data = r.json()
    assert data["document_ids"] == [id1, id2]
    assert len(data["summary"]) > 0


def test_multi_ask_empty_list(client: TestClient) -> None:
    r = client.post("/documents/multi/ask", json={
        "document_ids": [],
        "question": "anything",
    })
    assert r.status_code == 400


def test_multi_ask_missing_document(client: TestClient) -> None:
    r = client.post("/documents/multi/ask", json={
        "document_ids": ["nonexistent-id"],
        "question": "anything",
    })
    assert r.status_code == 404


def test_multi_summarize_with_style(client: TestClient, temp_data_dir: Path) -> None:
    doc = temp_data_dir / "styled.txt"
    doc.write_text("Some content to summarize briefly.")
    doc_id = _upload(client, doc, "styled.txt")

    r = client.post("/documents/multi/summarize", json={
        "document_ids": [doc_id],
        "max_length": 50,
        "style": "brief",
    })
    assert r.status_code == 200
    assert "summary" in r.json()
