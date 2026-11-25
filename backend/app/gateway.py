"""LiteLLM gateway with ordered key failover and built-in caching.

LiteLLM owns provider transport, caching and usage normalization. This module
adds the small, deterministic layer the assignment needs on top: per-key
identity, exact fallback counts, request-scoped failure simulation, a stable
cache key that survives key and session changes, and a single domain error when
the pool is exhausted.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from .cache_key import build_cache_key
from .config import Settings
from .errors import AllProvidersUnavailable

logger = logging.getLogger("lyftr.gateway")

_KEY_ATTEMPT_FAILURE_STATUSES = {401, 403, 408, 409, 425, 429}
_FAILOVER_EXCEPTION_NAMES = {
    "RateLimitError",
    "QuotaExceededError",
    "Timeout",
    "APITimeoutError",
    "APIConnectionError",
    "AuthenticationError",
    "PermissionDeniedError",
    "ServiceUnavailableError",
    "InternalServerError",
    "BadGatewayError",
    "APIError",
}


@dataclass(frozen=True, slots=True)
class GatewayResult:
    reply: str
    resolution_source: str
    model: str
    input_tokens: int
    output_tokens: int
    key_id: str | None
    fallback_attempts: int


class LLMGateway(Protocol):
    """The seam the chat service depends on, faked in the test suite."""

    cache_enabled: bool
    keys_configured: int

    async def startup(self) -> None: ...
    async def shutdown(self) -> None: ...
    async def complete(
        self,
        messages: list[dict[str, str]],
        simulation: Mapping[str, int],
    ) -> GatewayResult: ...


def is_failover_eligible(exc: BaseException) -> bool:
    """Classify provider failures that should try the next key."""

    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return True

    status = getattr(exc, "status_code", None)
    if not isinstance(status, int):
        status = getattr(exc, "code", None)
    if isinstance(status, int):
        if status in _KEY_ATTEMPT_FAILURE_STATUSES or 500 <= status <= 599:
            return True

    if exc.__class__.__name__ in _FAILOVER_EXCEPTION_NAMES:
        return True

    module = exc.__class__.__module__
    return module.startswith(("litellm", "openai", "google", "httpx"))


def _is_cache_hit(response: Any) -> bool:
    hidden_params = getattr(response, "_hidden_params", None)
    if isinstance(hidden_params, Mapping) and hidden_params.get("cache_hit") is True:
        return True
    return bool(getattr(response, "cache_hit", False))


def _extract_text(response: Any) -> str:
    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, TypeError):
        return ""

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, Mapping):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
            else:
                text = getattr(item, "text", None)
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts).strip()

    return str(content).strip() if content is not None else ""


def _extract_usage(response: Any) -> tuple[int, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return 0, 0

    input_tokens = getattr(usage, "prompt_tokens", None)
    if input_tokens is None:
        input_tokens = getattr(usage, "input_tokens", 0)

    output_tokens = getattr(usage, "completion_tokens", None)
    if output_tokens is None:
        output_tokens = getattr(usage, "output_tokens", 0)

    return int(input_tokens or 0), int(output_tokens or 0)


async def _flush_pending_cache_writes() -> None:
    """Await LiteLLM's background cache write before returning to the user.

    Recent LiteLLM releases persist completions in a background task. Awaiting
    those tasks makes an immediate repeat request deterministic instead of
    racing the writer. The import is intentionally defensive: it is an internal
    hook, and a missing hook must never break a successful reply.
    """

    try:
        from litellm.caching.caching_handler import _PENDING_CACHE_WRITES
    except Exception:  # pragma: no cover - version-dependent internals
        await asyncio.sleep(0)
        return

    pending = [task for task in list(_PENDING_CACHE_WRITES) if not task.done()]
    if pending:
        await asyncio.wait(pending, timeout=1.0)


class LiteLLMGateway:
    """Production gateway: one LiteLLM call per key, cache-first on each call."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._keys = settings.api_key_pool
        self._started = False
        self._cache_enabled = False

    @property
    def cache_enabled(self) -> bool:
        return self._cache_enabled

    @property
    def keys_configured(self) -> int:
        return len(self._keys)

    async def startup(self) -> None:
        if self._started:
            return

        import litellm
        from litellm.caching.caching import Cache

        litellm.suppress_debug_info = True
        litellm.drop_params = True
        litellm.cache = Cache(type="local", ttl=self._settings.cache_ttl_seconds)
        self._cache_enabled = True
        self._started = True
        logger.info(
            "gateway_ready model=%s keys=%s cache_ttl_seconds=%s",
            self._settings.llm_model,
            len(self._keys),
            self._settings.cache_ttl_seconds,
        )

    async def shutdown(self) -> None:
        try:
            import litellm

            litellm.cache = None
        except Exception:  # pragma: no cover - best effort during shutdown
            pass
        self._cache_enabled = False
        self._started = False

    async def complete(
        self,
        messages: list[dict[str, str]],
        simulation: Mapping[str, int],
    ) -> GatewayResult:
        if not self._started:
            await self.startup()

        import litellm

        settings = self._settings
        cache_key = build_cache_key(
            model=settings.llm_model,
            messages=messages,
            temperature=settings.llm_temperature,
            max_output_tokens=settings.llm_max_output_tokens,
        )
        simulation_active = bool(simulation)
        cache_options: dict[str, bool] = (
            {"no-cache": True, "no-store": True} if simulation_active else {}
        )

        deadline = time.monotonic() + settings.request_timeout_seconds
        failed_attempts = 0

        for key in self._keys:
            if key.id in simulation:
                failed_attempts += 1
                logger.warning(
                    "provider_attempt_simulated_failure key_id=%s status=%s",
                    key.id,
                    simulation[key.id],
                )
                continue

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break

            attempt_timeout = min(settings.key_attempt_timeout_seconds, remaining)
            attempt_started = time.perf_counter()

            try:
                response = await asyncio.wait_for(
                    litellm.acompletion(
                        model=settings.llm_model,
                        messages=messages,
                        api_key=key.value,
                        temperature=settings.llm_temperature,
                        max_tokens=settings.llm_max_output_tokens,
                        timeout=attempt_timeout,
                        num_retries=0,
                        cache=cache_options,
                        cache_key=cache_key,
                    ),
                    timeout=attempt_timeout,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if not is_failover_eligible(exc):
                    logger.error(
                        "provider_attempt_unexpected_error key_id=%s error=%s",
                        key.id,
                        type(exc).__name__,
                    )
                    raise
                failed_attempts += 1
                logger.warning(
                    "provider_attempt_failed key_id=%s status=%s error=%s "
                    "elapsed_ms=%s",
                    key.id,
                    getattr(exc, "status_code", None),
                    type(exc).__name__,
                    int((time.perf_counter() - attempt_started) * 1000),
                )
                continue

            reply = _extract_text(response)
            if not reply:
                failed_attempts += 1
                logger.warning(
                    "provider_attempt_empty_completion key_id=%s", key.id
                )
                continue

            cached = _is_cache_hit(response)
            input_tokens, output_tokens = _extract_usage(response)

            if not cached:
                await _flush_pending_cache_writes()

            return GatewayResult(
                reply=reply,
                resolution_source="LLM_CACHE" if cached else "LIVE_INFERENCE",
                model=settings.llm_model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                key_id=None if cached else key.id,
                fallback_attempts=0 if cached else failed_attempts,
            )

        logger.error(
            "provider_pool_exhausted keys=%s failed_attempts=%s simulated=%s",
            len(self._keys),
            failed_attempts,
            simulation_active,
        )
        raise AllProvidersUnavailable()
