"""Tests for document tagging and language features."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _upload_txt(client: TestClient, sample_txt_file: Path) -> str:
    with open(sample_txt_file, "rb") as f:
        resp = client.post("/documents", files={"file": ("test.txt", f, "text/plain")})
    assert resp.status_code == 201
    return resp.json()["document_id"]


def test_upload_returns_language_field(client: TestClient, sample_txt_file: Path) -> None:
    doc_id = _upload_txt(client, sample_txt_file)
    resp = client.get(f"/documents/{doc_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "language" in data
    assert "tags" in data
    assert isinstance(data["tags"], list)


def test_set_tags_endpoint(client: TestClient, sample_txt_file: Path) -> None:
    doc_id = _upload_txt(client, sample_txt_file)

    resp = client.put(f"/documents/{doc_id}/tags", json={"tags": ["finance", "q1-2025"]})
    assert resp.status_code == 200
    data = resp.json()
    assert set(data["tags"]) == {"finance", "q1-2025"}


def test_set_tags_replaces_existing(client: TestClient, sample_txt_file: Path) -> None:
    doc_id = _upload_txt(client, sample_txt_file)

    client.put(f"/documents/{doc_id}/tags", json={"tags": ["old-tag"]})
    resp = client.put(f"/documents/{doc_id}/tags", json={"tags": ["new-tag"]})
    assert resp.status_code == 200
    assert resp.json()["tags"] == ["new-tag"]


def test_set_tags_not_found(client: TestClient) -> None:
    import uuid
    fake_id = str(uuid.uuid4())
    resp = client.put(f"/documents/{fake_id}/tags", json={"tags": ["x"]})
    assert resp.status_code == 404


def test_list_documents_filter_by_tag(client: TestClient, sample_txt_file: Path) -> None:
    doc_id = _upload_txt(client, sample_txt_file)
    client.put(f"/documents/{doc_id}/tags", json={"tags": ["special-tag"]})

    resp = client.get("/documents?tag=special-tag")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    assert all("special-tag" in d["tags"] for d in data["documents"])


def test_list_documents_filter_no_match(client: TestClient) -> None:
    resp = client.get("/documents?tag=nonexistent-tag-xyz")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


def test_get_document_includes_tags_after_set(client: TestClient, sample_txt_file: Path) -> None:
    doc_id = _upload_txt(client, sample_txt_file)
    client.put(f"/documents/{doc_id}/tags", json={"tags": ["report", "2025"]})

    resp = client.get(f"/documents/{doc_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "report" in data["tags"]
    assert "2025" in data["tags"]
