"""Tests for streaming endpoints (SSE) with mock backend."""

from pathlib import Path

from fastapi.testclient import TestClient


def _upload(client: TestClient, file_path: Path) -> str:
    with open(file_path, "rb") as f:
        r = client.post("/documents", files={"file": ("test.txt", f, "text/plain")})
    assert r.status_code == 201
    return r.json()["document_id"]


def _collect_sse(response) -> list[str]:
    """Parse SSE response into a list of data values."""
    events = []
    for line in response.text.splitlines():
        if line.startswith("data: "):
            events.append(line[len("data: "):])
    return events


def test_summarize_stream_returns_sse(client: TestClient, sample_txt_file: Path) -> None:
    doc_id = _upload(client, sample_txt_file)
    response = client.post(f"/documents/{doc_id}/summarize/stream", json={})

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    events = _collect_sse(response)
    assert len(events) > 1
    assert events[-1] == "[DONE]"
    # All non-DONE events should be non-empty text chunks
    content_events = [e for e in events if e != "[DONE]"]
    assert len(content_events) > 0


def test_summarize_stream_nonexistent_doc(client: TestClient) -> None:
    response = client.post("/documents/no-such-doc/summarize/stream", json={})
    assert response.status_code == 404


def test_ask_stream_returns_sse(client: TestClient, sample_txt_file: Path) -> None:
    doc_id = _upload(client, sample_txt_file)
    response = client.post(
        f"/documents/{doc_id}/ask/stream",
        json={"question": "What is this document about?"},
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    events = _collect_sse(response)
    assert len(events) > 1
    assert events[-1] == "[DONE]"
    content_events = [e for e in events if e != "[DONE]"]
    assert len(content_events) > 0


def test_ask_stream_nonexistent_doc(client: TestClient) -> None:
    response = client.post(
        "/documents/no-such-doc/ask/stream",
        json={"question": "anything"},
    )
    assert response.status_code == 404


def test_ask_stream_missing_question(client: TestClient, sample_txt_file: Path) -> None:
    doc_id = _upload(client, sample_txt_file)
    response = client.post(f"/documents/{doc_id}/ask/stream", json={})
    assert response.status_code == 422
