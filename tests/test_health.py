"""Tests for health endpoint."""

from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """Test health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["backend"] == "mock"
    assert data["model"] == "mock-model"
    assert data["version"] == "0.1.0"
    assert "timestamp" in data


def test_health_check_returns_correct_structure(client: TestClient) -> None:
    """Test health check returns all required fields."""
    response = client.get("/health")
    data = response.json()

    required_fields = ["status", "backend", "model", "version", "timestamp"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
