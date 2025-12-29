"""Pytest configuration and fixtures."""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="function")
def temp_data_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        yield temp_path


@pytest.fixture(scope="function", autouse=True)
def setup_test_env(temp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Setup test environment variables."""
    # Set environment variables BEFORE importing anything
    monkeypatch.setenv("LLM_BACKEND", "mock")
    monkeypatch.setenv("LLM_MODEL", "mock-model")
    monkeypatch.setenv("DOCUMENTS_DIR", str(temp_data_dir / "documents"))
    monkeypatch.setenv("METADATA_FILE", str(temp_data_dir / "metadata.json"))
    monkeypatch.setenv("LOG_LEVEL", "ERROR")


@pytest.fixture(scope="function")
def client(setup_test_env: None) -> TestClient:
    """Create a test client with fresh imports."""
    # Import AFTER environment is set
    import sys

    # Clear module cache for clean reload
    modules_to_clear = [key for key in sys.modules.keys() if key.startswith('app.')]
    for module in modules_to_clear:
        del sys.modules[module]

    # Now import with fresh settings
    from app.main import app

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
