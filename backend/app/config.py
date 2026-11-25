"""Typed, environment-driven application settings.

Every configuration value enters the process here. API key material is wrapped
in :class:`ApiKey`, whose value is excluded from ``repr`` so a stray log line
cannot leak a secret.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SYSTEM_PROMPT = (
    "You are Lyftr AI, a concise and helpful assistant. Answer clearly and "
    "directly in plain language. Keep responses brief unless the user asks "
    "for detail."
)


@dataclass(frozen=True, slots=True)
class ApiKey:
    """One provider credential, addressed by a non-secret id."""

    id: str
    value: str = field(repr=False)


class Settings(BaseSettings):
    """Validated process configuration.

    Names map case-insensitively to environment variables, e.g.
    ``llm_api_keys`` reads ``LLM_API_KEYS``.
    """

    model_config = SettingsConfigDict(
        # Works both from the repo root and from backend/ (local dev runs
        # uvicorn from backend/, Docker injects real env vars instead).
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    llm_api_keys: str = ""
    llm_model: str = "gemini/gemini-3.5-flash-lite"
    database_url: str = "sqlite:///./lyftr.db"
    allowed_origins: str = "http://localhost:3000"
    enable_failure_simulation: bool = False
    default_system_prompt: str = DEFAULT_SYSTEM_PROMPT
    cache_ttl_seconds: int = Field(default=3600, ge=1)
    key_attempt_timeout_seconds: float = Field(default=30.0, gt=0)
    request_timeout_seconds: float = Field(default=60.0, gt=0)
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    llm_max_output_tokens: int = Field(default=1024, ge=1, le=32768)
    log_level: str = "INFO"
    port: int = Field(default=8000, ge=1, le=65535)
    enable_docs: bool = False

    @field_validator("llm_model", "database_url")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("default_system_prompt")
    @classmethod
    def _validate_default_prompt(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("DEFAULT_SYSTEM_PROMPT must not be blank")
        return value

    @model_validator(mode="after")
    def _validate_environment(self) -> "Settings":
        # Accessing the pool validates count, uniqueness and emptiness.
        _ = self.api_key_pool

        if not self.allowed_origins_list:
            raise ValueError("ALLOWED_ORIGINS must contain at least one origin")
        if "*" in self.allowed_origins_list:
            raise ValueError("ALLOWED_ORIGINS must not contain a wildcard")

        if not self.database_url.startswith("sqlite"):
            raise ValueError("DATABASE_URL must be a SQLite URL (sqlite:///...)")

        return self

    @property
    def api_key_pool(self) -> tuple[ApiKey, ...]:
        """Ordered key pool, assigned ``key_1`` ... ``key_n``."""

        parts = [part.strip() for part in self.llm_api_keys.split(",")]
        values = [part for part in parts if part]

        if len(values) < 2:
            raise ValueError(
                "LLM_API_KEYS must contain at least 2 comma-separated API keys"
            )
        if len(set(values)) != len(values):
            raise ValueError("LLM_API_KEYS must not contain duplicate keys")

        return tuple(
            ApiKey(id=f"key_{index}", value=value)
            for index, value in enumerate(values, start=1)
        )

    @property
    def key_ids(self) -> tuple[str, ...]:
        return tuple(key.id for key in self.api_key_pool)

    @property
    def keys_configured(self) -> int:
        return len(self.api_key_pool)

    @property
    def allowed_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]
