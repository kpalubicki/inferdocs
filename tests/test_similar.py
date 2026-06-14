"""Tests for GET /documents/{id}/similar endpoint."""

import pytest
from fastapi.testclient import TestClient


def _upload(client: TestClient, name: str, content: str) -> str:
    r = client.post("/documents", files={"file": (name, content.encode(), "text/plain")})
    assert r.status_code == 201
    return r.json()["document_id"]


def test_similar_returns_empty_when_only_one_doc(client: TestClient) -> None:
    doc_id = _upload(client, "a.txt", "Python web development with FastAPI and REST APIs")
    r = client.get(f"/documents/{doc_id}/similar")
    assert r.status_code == 200
    data = r.json()
    assert data["document_id"] == doc_id
    assert data["results"] == []


def test_similar_finds_related_document(client: TestClient) -> None:
    id_a = _upload(client, "a.txt", "Python machine learning deep learning neural networks")
    id_b = _upload(client, "b.txt", "Python machine learning scikit-learn classification")
    id_c = _upload(client, "c.txt", "cooking recipes pasta italian cuisine food preparation")

    r = client.get(f"/documents/{id_a}/similar?top=5")
    assert r.status_code == 200
    data = r.json()
    # b should be more similar to a than c (shared ML vocabulary)
    ids_in_order = [item["document_id"] for item in data["results"]]
    assert id_b in ids_in_order
    b_pos = ids_in_order.index(id_b)
    c_pos = ids_in_order.index(id_c)
    assert b_pos < c_pos


def test_similar_does_not_include_target_document(client: TestClient) -> None:
    id_a = _upload(client, "a.txt", "Python programming language")
    _upload(client, "b.txt", "Python programming tutorial")
    r = client.get(f"/documents/{id_a}/similar")
    data = r.json()
    result_ids = [item["document_id"] for item in data["results"]]
    assert id_a not in result_ids


def test_similar_respects_top_param(client: TestClient) -> None:
    id_a = _upload(client, "a.txt", "data science analytics")
    for i in range(5):
        _upload(client, f"doc{i}.txt", f"data science analytics statistics topic {i}")

    r = client.get(f"/documents/{id_a}/similar?top=2")
    assert r.status_code == 200
    assert len(r.json()["results"]) <= 2


def test_similar_top_n_in_response(client: TestClient) -> None:
    id_a = _upload(client, "a.txt", "content")
    r = client.get(f"/documents/{id_a}/similar?top=3")
    assert r.json()["top_n"] == 3


def test_similar_invalid_top_too_low(client: TestClient) -> None:
    id_a = _upload(client, "a.txt", "some text")
    r = client.get(f"/documents/{id_a}/similar?top=0")
    assert r.status_code == 422


def test_similar_invalid_top_too_high(client: TestClient) -> None:
    id_a = _upload(client, "a.txt", "some text")
    r = client.get(f"/documents/{id_a}/similar?top=99")
    assert r.status_code == 422


def test_similar_returns_404_for_missing_doc(client: TestClient) -> None:
    r = client.get("/documents/nonexistent-id/similar")
    assert r.status_code == 404


def test_similar_result_includes_score_and_filename(client: TestClient) -> None:
    id_a = _upload(client, "a.txt", "software engineering testing debugging")
    _upload(client, "b.txt", "software testing unit tests debugging")
    r = client.get(f"/documents/{id_a}/similar?top=5")
    results = r.json()["results"]
    assert len(results) >= 1
    assert "score" in results[0]
    assert "filename" in results[0]
    assert "document_id" in results[0]
    assert 0.0 <= results[0]["score"] <= 1.0


# --- unit tests for similarity module ---

def test_similarity_module_cosine_identical():
    from app.services.documents.similarity import find_similar
    text = "python web api fastapi rest endpoints"
    result = find_similar(text, [("doc1", text)], top_n=1)
    assert len(result) == 1
    assert result[0][0] == "doc1"
    assert result[0][1] > 0.9


def test_similarity_module_unrelated_low_score():
    from app.services.documents.similarity import find_similar
    a = "python programming code software"
    b = "cooking food pasta italian restaurant"
    result = find_similar(a, [("doc1", b)], top_n=1)
    assert result[0][1] < 0.5


def test_similarity_module_empty_candidates():
    from app.services.documents.similarity import find_similar
    result = find_similar("some text", [], top_n=5)
    assert result == []


def test_similarity_module_top_n_honored():
    from app.services.documents.similarity import find_similar
    target = "python web"
    candidates = [(f"doc{i}", f"python web {i}") for i in range(10)]
    result = find_similar(target, candidates, top_n=3)
    assert len(result) == 3
