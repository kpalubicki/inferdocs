"""Tests for document endpoints."""

from pathlib import Path

from fastapi.testclient import TestClient


def test_upload_txt_document(client: TestClient, sample_txt_file: Path) -> None:
    """Test uploading a text document."""
    with open(sample_txt_file, "rb") as f:
        response = client.post(
            "/documents",
            files={"file": ("test.txt", f, "text/plain")},
        )

    assert response.status_code == 201
    data = response.json()

    assert "document_id" in data
    assert data["filename"] == "test.txt"
    assert data["message"] == "Document uploaded successfully"


def test_upload_md_document(client: TestClient, sample_md_file: Path) -> None:
    """Test uploading a markdown document."""
    with open(sample_md_file, "rb") as f:
        response = client.post(
            "/documents",
            files={"file": ("test.md", f, "text/markdown")},
        )

    assert response.status_code == 201
    data = response.json()

    assert "document_id" in data
    assert data["filename"] == "test.md"


def test_upload_unsupported_file_type(client: TestClient, temp_data_dir: Path) -> None:
    """Test uploading an unsupported file type."""
    unsupported_file = temp_data_dir / "test.xyz"
    unsupported_file.write_text("test content")

    with open(unsupported_file, "rb") as f:
        response = client.post(
            "/documents",
            files={"file": ("test.xyz", f, "application/octet-stream")},
        )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_list_documents_empty(client: TestClient) -> None:
    """Test listing documents when none exist."""
    response = client.get("/documents")

    assert response.status_code == 200
    data = response.json()

    assert data["count"] == 0
    assert data["documents"] == []


def test_list_documents_after_upload(client: TestClient, sample_txt_file: Path) -> None:
    """Test listing documents after uploading one."""
    # Upload a document
    with open(sample_txt_file, "rb") as f:
        client.post("/documents", files={"file": ("test.txt", f, "text/plain")})

    # List documents
    response = client.get("/documents")

    assert response.status_code == 200
    data = response.json()

    assert data["count"] == 1
    assert len(data["documents"]) == 1
    assert data["documents"][0]["filename"] == "test.txt"
    assert data["documents"][0]["file_type"] == ".txt"


def test_get_document_metadata(client: TestClient, sample_txt_file: Path) -> None:
    """Test fetching metadata for a single document."""
    with open(sample_txt_file, "rb") as f:
        upload = client.post("/documents", files={"file": ("test.txt", f, "text/plain")})
    document_id = upload.json()["document_id"]

    response = client.get(f"/documents/{document_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == document_id
    assert data["filename"] == "test.txt"
    assert data["file_type"] == ".txt"
    assert "file_size" in data
    assert "upload_time" in data


def test_get_document_not_found(client: TestClient) -> None:
    """Test fetching metadata for a non-existent document."""
    response = client.get("/documents/nonexistent-id")
    assert response.status_code == 404


def test_upload_without_file(client: TestClient) -> None:
    """Test upload endpoint without providing a file."""
    response = client.post("/documents")

    assert response.status_code == 422  # Unprocessable Entity


def test_upload_file_too_large(client: TestClient, temp_data_dir: Path) -> None:
    """Test uploading a file that exceeds size limit."""
    large_file = temp_data_dir / "large.txt"
    large_content = b"x" * (11 * 1024 * 1024)  # 11MB (exceeds 10MB limit)
    large_file.write_bytes(large_content)

    with open(large_file, "rb") as f:
        response = client.post(
            "/documents",
            files={"file": ("large.txt", f, "text/plain")},
        )

    assert response.status_code == 413
    data = response.json()
    assert "detail" in data
    assert "10MB" in data["detail"]
