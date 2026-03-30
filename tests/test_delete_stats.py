"""Tests for document deletion and usage stats endpoints."""

from pathlib import Path

from fastapi.testclient import TestClient


def _upload(client: TestClient, file_path: Path, name: str = "test.txt") -> str:
    with open(file_path, "rb") as f:
        r = client.post("/documents", files={"file": (name, f, "text/plain")})
    assert r.status_code == 201
    return r.json()["document_id"]


def test_delete_document(client: TestClient, sample_txt_file: Path) -> None:
    doc_id = _upload(client, sample_txt_file)

    r = client.delete(f"/documents/{doc_id}")
    assert r.status_code == 200
    assert r.json()["document_id"] == doc_id
    assert r.json()["message"] == "Document deleted"


def test_delete_removes_from_list(client: TestClient, sample_txt_file: Path) -> None:
    doc_id = _upload(client, sample_txt_file)

    client.delete(f"/documents/{doc_id}")

    r = client.get("/documents")
    ids = [d["document_id"] for d in r.json()["documents"]]
    assert doc_id not in ids


def test_delete_nonexistent(client: TestClient) -> None:
    r = client.delete("/documents/does-not-exist")
    assert r.status_code == 404


def test_stats_empty(client: TestClient) -> None:
    r = client.get("/documents/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["document_count"] == 0
    assert data["total_size_bytes"] == 0
    assert data["total_size_mb"] == 0.0
    assert data["file_types"] == {}


def test_stats_with_documents(client: TestClient, sample_txt_file: Path, sample_md_file: Path) -> None:
    _upload(client, sample_txt_file, "a.txt")
    _upload(client, sample_md_file, "b.md")

    r = client.get("/documents/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["document_count"] == 2
    assert data["total_size_bytes"] > 0
    assert data["file_types"][".txt"] == 1
    assert data["file_types"][".md"] == 1
