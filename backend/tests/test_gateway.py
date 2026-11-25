from __future__ import annotations

import asyncio

import pytest

from app.errors import AllProvidersUnavailable
from app.gateway import LiteLLMGateway, is_failover_eligible

from .conftest import make_settings


class ProviderError(Exception):
    def __init__(self, status_code: int, message: str = "provider error") -> None:
        super().__init__(message)
        self.status_code = status_code


class Usage:
    def __init__(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class Message:
    def __init__(self, content: str) -> None:
        self.content = content


class Choice:
    def __init__(self, content: str) -> None:
        self.message = Message(content)


class Response:
    def __init__(
        self,
        content: str,
        *,
        prompt_tokens: int = 11,
        completion_tokens: int = 7,
        cache_hit: bool = False,
    ) -> None:
        self.choices = [Choice(content)]
        self.usage = Usage(prompt_tokens, completion_tokens)
        self._hidden_params = {"cache_hit": True} if cache_hit else {}


MESSAGES = [
    {"role": "system", "content": "Be concise."},
    {"role": "user", "content": "Hello"},
]


def gateway_for(tmp_path) -> LiteLLMGateway:
    gateway = LiteLLMGateway(make_settings(tmp_path))
    gateway._started = True  # unit tests inject the transport, not the cache
    gateway._cache_enabled = True
    return gateway


async def test_first_key_success_has_zero_fallbacks(monkeypatch, tmp_path):
    gateway = gateway_for(tmp_path)
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        return Response("Hi there")

    monkeypatch.setattr("litellm.acompletion", fake_acompletion)

    result = await gateway.complete(MESSAGES, {})

    assert result.reply == "Hi there"
    assert result.resolution_source == "LIVE_INFERENCE"
    assert result.key_id == "key_1"
    assert result.fallback_attempts == 0
    assert result.input_tokens == 11
    assert result.output_tokens == 7
    assert len(calls) == 1
    assert calls[0]["api_key"] == "test-key-alpha"
    assert calls[0]["num_retries"] == 0
    assert calls[0]["cache_key"].startswith("lyftr:v1:")


async def test_rate_limited_first_key_fails_over(monkeypatch, tmp_path):
    gateway = gateway_for(tmp_path)
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        if kwargs["api_key"] == "test-key-alpha":
            raise ProviderError(429)
        return Response("From the second key")

    monkeypatch.setattr("litellm.acompletion", fake_acompletion)

    result = await gateway.complete(MESSAGES, {})

    assert result.reply == "From the second key"
    assert result.key_id == "key_2"
    assert result.fallback_attempts == 1
    assert result.resolution_source == "LIVE_INFERENCE"
    assert len(calls) == 2
    assert calls[0]["cache_key"] == calls[1]["cache_key"]


async def test_server_error_first_key_fails_over(monkeypatch, tmp_path):
    gateway = gateway_for(tmp_path)

    async def fake_acompletion(**kwargs):
        if kwargs["api_key"] == "test-key-alpha":
            raise ProviderError(503)
        return Response("Second key answer")

    monkeypatch.setattr("litellm.acompletion", fake_acompletion)

    result = await gateway.complete(MESSAGES, {})
    assert result.key_id == "key_2"
    assert result.fallback_attempts == 1


async def test_timeout_is_failover_eligible(monkeypatch, tmp_path):
    gateway = gateway_for(tmp_path)

    async def fake_acompletion(**kwargs):
        if kwargs["api_key"] == "test-key-alpha":
            raise asyncio.TimeoutError()
        return Response("Second key after timeout")

    monkeypatch.setattr("litellm.acompletion", fake_acompletion)

    result = await gateway.complete(MESSAGES, {})
    assert result.key_id == "key_2"
    assert result.fallback_attempts == 1


async def test_empty_completion_fails_over(monkeypatch, tmp_path):
    gateway = gateway_for(tmp_path)

    async def fake_acompletion(**kwargs):
        if kwargs["api_key"] == "test-key-alpha":
            return Response("   ")
        return Response("A real answer")

    monkeypatch.setattr("litellm.acompletion", fake_acompletion)

    result = await gateway.complete(MESSAGES, {})
    assert result.reply == "A real answer"
    assert result.key_id == "key_2"
    assert result.fallback_attempts == 1


async def test_all_keys_failing_raises_domain_error(monkeypatch, tmp_path):
    gateway = gateway_for(tmp_path)

    async def fake_acompletion(**kwargs):
        raise ProviderError(429)

    monkeypatch.setattr("litellm.acompletion", fake_acompletion)

    with pytest.raises(AllProvidersUnavailable):
        await gateway.complete(MESSAGES, {})


async def test_cache_hit_is_normalized(monkeypatch, tmp_path):
    gateway = gateway_for(tmp_path)
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        return Response(
            "Cached answer",
            prompt_tokens=42,
            completion_tokens=9,
            cache_hit=True,
        )

    monkeypatch.setattr("litellm.acompletion", fake_acompletion)

    result = await gateway.complete(MESSAGES, {})

    assert result.reply == "Cached answer"
    assert result.resolution_source == "LLM_CACHE"
    assert result.key_id is None
    assert result.fallback_attempts == 0
    assert result.input_tokens == 42
    assert result.output_tokens == 9
    assert calls[0]["cache"] == {}


async def test_cache_hit_after_failed_key_still_reports_zero_fallbacks(
    monkeypatch, tmp_path
):
    gateway = gateway_for(tmp_path)

    async def fake_acompletion(**kwargs):
        if kwargs["api_key"] == "test-key-alpha":
            raise ProviderError(500)
        return Response("Cached later", cache_hit=True)

    monkeypatch.setattr("litellm.acompletion", fake_acompletion)

    result = await gateway.complete(MESSAGES, {})
    assert result.resolution_source == "LLM_CACHE"
    assert result.key_id is None
    assert result.fallback_attempts == 0


async def test_simulated_failure_skips_key_and_bypasses_cache(
    monkeypatch, tmp_path
):
    gateway = gateway_for(tmp_path)
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        return Response("Real second-key answer")

    monkeypatch.setattr("litellm.acompletion", fake_acompletion)

    result = await gateway.complete(MESSAGES, {"key_1": 429})

    assert result.reply == "Real second-key answer"
    assert result.key_id == "key_2"
    assert result.fallback_attempts == 1
    assert len(calls) == 1
    assert calls[0]["api_key"] == "test-key-beta"
    assert calls[0]["cache"] == {"no-cache": True, "no-store": True}


async def test_wildcard_simulation_fails_without_any_provider_call(
    monkeypatch, tmp_path
):
    gateway = gateway_for(tmp_path)
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        return Response("should never happen")

    monkeypatch.setattr("litellm.acompletion", fake_acompletion)

    with pytest.raises(AllProvidersUnavailable):
        await gateway.complete(
            MESSAGES, {"key_1": 429, "key_2": 429}
        )

    assert calls == []


async def test_unexpected_programming_error_is_not_hidden(monkeypatch, tmp_path):
    gateway = gateway_for(tmp_path)

    async def fake_acompletion(**kwargs):
        raise ValueError("bad application state")

    monkeypatch.setattr("litellm.acompletion", fake_acompletion)

    with pytest.raises(ValueError):
        await gateway.complete(MESSAGES, {})


def test_failover_classification_by_status_code():
    assert is_failover_eligible(ProviderError(429))
    assert is_failover_eligible(ProviderError(500))
    assert is_failover_eligible(ProviderError(502))
    assert is_failover_eligible(ProviderError(401))
    assert not is_failover_eligible(ProviderError(400))
    assert is_failover_eligible(asyncio.TimeoutError())


def test_failover_classification_by_class_name():
    class RateLimitError(Exception):
        pass

    assert is_failover_eligible(RateLimitError())
