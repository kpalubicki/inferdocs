"""Application configuration management."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: str = "dev"
    app_version: str = "0.1.0"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # LLM Configuration
    llm_backend: Literal["ollama", "vllm", "mock"] = "ollama"
    llm_model: str = "default"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"

    # vLLM
    vllm_base_url: str = "http://localhost:8000"

    # Document Storage
    documents_dir: str = "./data/documents"
    metadata_file: str = "./data/metadata.json"
    max_upload_size_mb: int = 10

    # Logging
    log_level: str = "INFO"

    @property
    def llm_base_url(self) -> str:
        """Get the base URL for the current LLM backend."""
        if self.llm_backend == "ollama":
            return self.ollama_base_url
        elif self.llm_backend == "vllm":
            return self.vllm_base_url
        return ""

    @property
    def resolved_model(self) -> str:
        """Resolve model alias to actual model name."""
        if self.llm_model != "default":
            return self.llm_model

        model_mapping = {
            "ollama": "qwen2.5:3b",
            "vllm": "meta-llama/Llama-3.1-8B-Instruct",
            "mock": "mock-model",
        }
        return model_mapping[self.llm_backend]


# Global settings instance
settings = Settings()
