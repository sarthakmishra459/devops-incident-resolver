from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DIR_",
        extra="ignore",
    )

    app_name: str = "Adaptive DevOps Incident Resolver"
    environment: Literal["local", "test", "staging", "production"] = "local"
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    database_url: PostgresDsn | None = None
    redis_url: RedisDsn | None = None
    rabbitmq_url: str | None = None

    llm_provider: Literal["local", "openai", "groq", "openai_compatible"] = "local"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    groq_api_key: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "llama-3.1-8b-instant"
    llm_temperature: float = 0.1
    llm_timeout_seconds: float = 25.0
    use_mock_llm: bool = False

    data_dir: Path = Path("data")
    upload_dir: Path = Path("data/uploads")
    vector_index_dir: Path = Path("data/faiss")
    max_reflection_retries: int = 3
    confidence_threshold: int = 80
    command_timeout_seconds: int = 6
    max_command_output_chars: int = 20_000

    @computed_field  # type: ignore[prop-decorator]
    @property
    def should_use_external_llm(self) -> bool:
        return bool(self.llm_api_key and not self.use_mock_llm)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def llm_api_key(self) -> str | None:
        if self.llm_provider == "groq":
            return self.groq_api_key
        if self.llm_provider in {"openai", "openai_compatible"}:
            return self.openai_api_key
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def llm_base_url(self) -> str | None:
        if self.llm_provider == "groq":
            return self.groq_base_url
        return self.openai_base_url

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_enabled(self) -> bool:
        return self.database_url is not None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_enabled(self) -> bool:
        return self.redis_url is not None


@lru_cache
def get_settings() -> Settings:
    return Settings()
