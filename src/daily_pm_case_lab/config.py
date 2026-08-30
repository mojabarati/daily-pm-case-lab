from __future__ import annotations

from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings with finite defaults and secret-safe values."""

    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
        populate_by_name=True,
    )

    openai_api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5.6-terra", alias="OPENAI_MODEL")
    max_case_candidates: int = Field(default=5, ge=1, le=10, alias="MAX_CASE_CANDIDATES")
    max_research_passes: int = Field(default=3, ge=1, le=5, alias="MAX_RESEARCH_PASSES")
    max_sources: int = Field(default=12, ge=5, le=20, alias="MAX_SOURCES")
    max_agent_runs: int = Field(default=12, ge=3, le=30, alias="MAX_AGENT_RUNS")
    log_level: str = Field(default="INFO", alias="PM_CASE_LOG_LEVEL")
    github_repository: str | None = Field(default=None, alias="PM_CASE_GITHUB_REPOSITORY")
    root_dir: Path = Field(default_factory=Path.cwd)

    @field_validator("openai_model")
    @classmethod
    def model_must_be_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("OPENAI_MODEL cannot be empty")
        return value.strip()

    @field_validator("github_repository")
    @classmethod
    def normalize_repository(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip()
        if normalized.count("/") != 1:
            raise ValueError("PM_CASE_GITHUB_REPOSITORY must be owner/repository")
        return normalized

    @property
    def data_dir(self) -> Path:
        return self.root_dir / "data"

    @property
    def cases_dir(self) -> Path:
        return self.root_dir / "cases"

    def require_api_key(self) -> None:
        if self.openai_api_key is None or not self.openai_api_key.get_secret_value().strip():
            raise RuntimeError("OPENAI_API_KEY is required for generation")
