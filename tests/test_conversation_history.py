"""Tests for conversation history recording and export endpoints."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _upload(client: TestClient, file_path: Path) -> str:
    with open(file_path, "rb") as f:
        r = client.post("/documents", files={"file": (file_path.name, f, "text/plain")})
    assert r.status_code == 201
    return r.json()["document_id"]


def _ask(client: TestClient, doc_id: str, question: str) -> None:
    r = client.post(f"/documents/{doc_id}/ask", json={"question": question})
    assert r.status_code == 200


def test_history_empty_after_upload(client: TestClient, sample_txt_file: Path):
    doc_id = _upload(client, sample_txt_file)
    r = client.get(f"/documents/{doc_id}/history")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 0
    assert data["entries"] == []
    assert data["document_id"] == doc_id


def test_history_records_qa(client: TestClient, sample_txt_file: Path):
    doc_id = _upload(client, sample_txt_file)
    _ask(client, doc_id, "What is this about?")
    _ask(client, doc_id, "Give me a summary.")

    r = client.get(f"/documents/{doc_id}/history")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 2
    questions = [e["question"] for e in data["entries"]]
    assert "What is this about?" in questions
    assert "Give me a summary." in questions


def test_history_entries_have_timestamps(client: TestClient, sample_txt_file: Path):
    doc_id = _upload(client, sample_txt_file)
    _ask(client, doc_id, "Test question")

    r = client.get(f"/documents/{doc_id}/history")
    entry = r.json()["entries"][0]
    assert "timestamp" in entry
    assert entry["timestamp"]  # non-empty


def test_history_not_found_for_missing_doc(client: TestClient):
    import uuid
    r = client.get(f"/documents/{uuid.uuid4()}/history")
    assert r.status_code == 404


def test_export_markdown(client: TestClient, sample_txt_file: Path):
    doc_id = _upload(client, sample_txt_file)
    _ask(client, doc_id, "What is this?")

    r = client.get(f"/documents/{doc_id}/history/export")
    assert r.status_code == 200
    assert "text/markdown" in r.headers["content-type"]
    assert "content-disposition" in r.headers
    assert "-history.md" in r.headers["content-disposition"]
    body = r.text
    assert "What is this?" in body
    assert "Mock response" in body  # answer from mock LLM


def test_export_json(client: TestClient, sample_txt_file: Path):
    doc_id = _upload(client, sample_txt_file)
    _ask(client, doc_id, "JSON export test")

    r = client.get(f"/documents/{doc_id}/history/export?format=json")
    assert r.status_code == 200
    assert "application/json" in r.headers["content-type"]
    assert "-history.json" in r.headers["content-disposition"]
    data = r.json()
    assert isinstance(data, list)
    assert data[0]["question"] == "JSON export test"


def test_export_empty_history_markdown(client: TestClient, sample_txt_file: Path):
    doc_id = _upload(client, sample_txt_file)
    r = client.get(f"/documents/{doc_id}/history/export")
    assert r.status_code == 200
    assert "No conversations recorded" in r.text


def test_export_not_found(client: TestClient):
    import uuid
    r = client.get(f"/documents/{uuid.uuid4()}/history/export")
    assert r.status_code == 404


def test_clear_history(client: TestClient, sample_txt_file: Path):
    doc_id = _upload(client, sample_txt_file)
    _ask(client, doc_id, "First question")
    _ask(client, doc_id, "Second question")

    r = client.delete(f"/documents/{doc_id}/history")
    assert r.status_code == 204

    r = client.get(f"/documents/{doc_id}/history")
    assert r.json()["count"] == 0


def test_clear_history_not_found(client: TestClient):
    import uuid
    r = client.delete(f"/documents/{uuid.uuid4()}/history")
    assert r.status_code == 404


def test_history_cleared_when_document_deleted(client: TestClient, sample_txt_file: Path):
    doc_id = _upload(client, sample_txt_file)
    _ask(client, doc_id, "Before delete")

    client.delete(f"/documents/{doc_id}")

    # Re-uploading to verify history file is gone — the doc is deleted so history 404s
    import uuid
    r = client.get(f"/documents/{doc_id}/history")
    assert r.status_code == 404


def test_history_filename_in_response(client: TestClient, sample_txt_file: Path):
    doc_id = _upload(client, sample_txt_file)
    r = client.get(f"/documents/{doc_id}/history")
    assert r.json()["filename"] == sample_txt_file.name
