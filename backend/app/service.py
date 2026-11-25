"""Chat orchestration: session locks, prompt semantics, persistence and timing."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .config import Settings
from .gateway import LLMGateway
from .repository import SessionRepository


@dataclass(frozen=True, slots=True)
class ChatServiceResult:
    session_id: str
    reply: str
    metadata: dict[str, Any]


class ChatService:
    """Owns the complete successful request path for one chat turn."""

    def __init__(
        self,
        repository: SessionRepository,
        gateway: LLMGateway,
        settings: Settings,
    ) -> None:
        self._repository = repository
        self._gateway = gateway
        self._settings = settings
        self._session_locks: dict[str, asyncio.Lock] = {}
        self._locks_guard = asyncio.Lock()

    async def _lock_for(self, session_id: str) -> asyncio.Lock:
        async with self._locks_guard:
            lock = self._session_locks.get(session_id)
            if lock is None:
                lock = asyncio.Lock()
                self._session_locks[session_id] = lock
            return lock

    async def chat(
        self,
        *,
        session_id: str,
        message: str,
        system_prompt: str | None,
        simulation: Mapping[str, int],
    ) -> ChatServiceResult:
        started = time.perf_counter()

        lock = await self._lock_for(session_id)
        async with lock:
            stored_prompt: str | None = None
            history: list[dict[str, str]] = []

            session = await self._repository.get_session(session_id)
            if session is not None:
                stored_prompt = session.system_prompt
                for record in await self._repository.get_messages(session_id):
                    if record.role in ("user", "assistant"):
                        history.append(
                            {"role": record.role, "content": record.content}
                        )

            if system_prompt is None:
                effective_prompt = (
                    stored_prompt or self._settings.default_system_prompt
                )
            else:
                # Validation has already trimmed the value. Empty means reset.
                effective_prompt = (
                    system_prompt or self._settings.default_system_prompt
                )

            messages: list[dict[str, str]] = [
                {"role": "system", "content": effective_prompt},
                *history,
                {"role": "user", "content": message},
            ]

            gateway_result = await self._gateway.complete(messages, simulation)

            latency_ms = max(
                1, int(round((time.perf_counter() - started) * 1000))
            )
            metadata: dict[str, Any] = {
                "resolution_source": gateway_result.resolution_source,
                "model": gateway_result.model,
                "latency_ms": latency_ms,
                "input_tokens": gateway_result.input_tokens,
                "output_tokens": gateway_result.output_tokens,
                "key_id": gateway_result.key_id,
                "fallback_attempts": gateway_result.fallback_attempts,
            }

            await self._repository.save_exchange(
                session_id=session_id,
                system_prompt=effective_prompt,
                user_content=message,
                assistant_content=gateway_result.reply,
                assistant_metadata=metadata,
            )

        return ChatServiceResult(
            session_id=session_id,
            reply=gateway_result.reply,
            metadata=metadata,
        )
