"""Pytest configuration and fixtures."""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.fixture(scope="session")
def temp_data_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        yield temp_path


@pytest.fixture(autouse=True)
def setup_test_env(temp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Setup test environment variables."""
    monkeypatch.setenv("LLM_BACKEND", "mock")
    monkeypatch.setenv("LLM_MODEL", "mock-model")
    monkeypatch.setenv("DOCUMENTS_DIR", str(temp_data_dir / "documents"))
    monkeypatch.setenv("METADATA_FILE", str(temp_data_dir / "metadata.json"))
    monkeypatch.setenv("LOG_LEVEL", "ERROR")

    # Force reload of settings
    from importlib import reload

    from app.core import config

    reload(config)


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def sample_txt_file(temp_data_dir: Path) -> Path:
    """Create a sample text file."""
    file_path = temp_data_dir / "sample.txt"
    file_path.write_text("This is a sample text document for testing.")
    return file_path


@pytest.fixture
def sample_md_file(temp_data_dir: Path) -> Path:
    """Create a sample markdown file."""
    file_path = temp_data_dir / "sample.md"
    content = """# Sample Document

This is a **markdown** document for testing.

## Features
- Feature 1
- Feature 2
"""
    file_path.write_text(content)
    return file_path
