"""Deterministic in-process gateway used by the API test suite.

It mirrors the production contract at the gateway seam: ordered key attempts,
request-scoped simulated failures, cache-first lookups with cross-session keys,
stored usage on cache hits, and one domain error when the pool is exhausted.
"""

from __future__ import annotations

import asyncio
import copy
from collections.abc import Mapping

from app.cache_key import build_cache_key
from app.config import Settings
from app.errors import AllProvidersUnavailable
from app.gateway import GatewayResult


def _count_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class FakeGateway:
    def __init__(self, settings: Settings, *, live_delay: float = 0.0) -> None:
        self.settings = settings
        self.keys = settings.api_key_pool
        self.keys_configured = len(self.keys)
        self.cache_enabled = True
        self.live_delay = live_delay
        self.cache: dict[str, GatewayResult] = {}
        self.calls: list[dict] = []
        self.live_calls: list[dict] = []

    async def startup(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    def _cache_key(self, messages: list[dict[str, str]]) -> str:
        return build_cache_key(
            model=self.settings.llm_model,
            messages=messages,
            temperature=self.settings.llm_temperature,
            max_output_tokens=self.settings.llm_max_output_tokens,
        )

    async def complete(
        self,
        messages: list[dict[str, str]],
        simulation: Mapping[str, int],
    ) -> GatewayResult:
        self.calls.append(
            {
                "messages": copy.deepcopy(messages),
                "simulation": dict(simulation),
            }
        )

        simulation_active = bool(simulation)
        cache_key = self._cache_key(messages)

        if not simulation_active and cache_key in self.cache:
            cached = self.cache[cache_key]
            return GatewayResult(
                reply=cached.reply,
                resolution_source="LLM_CACHE",
                model=cached.model,
                input_tokens=cached.input_tokens,
                output_tokens=cached.output_tokens,
                key_id=None,
                fallback_attempts=0,
            )

        self.live_calls.append(copy.deepcopy(messages))

        if self.live_delay:
            await asyncio.sleep(self.live_delay)

        failed_attempts = 0
        for key in self.keys:
            if key.id in simulation:
                failed_attempts += 1
                continue

            last_user_message = messages[-1]["content"] if messages else ""
            reply = f"Echo: {last_user_message}"
            prompt_text = "\n".join(item["content"] for item in messages)
            result = GatewayResult(
                reply=reply,
                resolution_source="LIVE_INFERENCE",
                model=self.settings.llm_model,
                input_tokens=_count_tokens(prompt_text),
                output_tokens=_count_tokens(reply),
                key_id=key.id,
                fallback_attempts=failed_attempts,
            )

            if not simulation_active:
                self.cache[cache_key] = result

            return result

        raise AllProvidersUnavailable()
