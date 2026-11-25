"""HTTP request and response models for the public contract."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

MAX_MESSAGE_CHARS = 4000
MAX_SESSION_ID_CHARS = 128


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=MAX_SESSION_ID_CHARS)
    message: str
    system_prompt: str | None = None

    @field_validator("session_id")
    @classmethod
    def _session_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("session_id must not be empty")
        return value

    @field_validator("message")
    @classmethod
    def _validate_message(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("message must not be empty")
        if len(trimmed) > MAX_MESSAGE_CHARS:
            raise ValueError(
                f"message must be at most {MAX_MESSAGE_CHARS} characters"
            )
        return trimmed

    @field_validator("system_prompt")
    @classmethod
    def _validate_system_prompt(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if len(trimmed) > MAX_MESSAGE_CHARS:
            raise ValueError(
                f"system_prompt must be at most {MAX_MESSAGE_CHARS} characters"
            )
        return trimmed


class ChatMetadata(BaseModel):
    resolution_source: Literal["LIVE_INFERENCE", "LLM_CACHE"]
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    key_id: str | None
    fallback_attempts: int


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    metadata: ChatMetadata
