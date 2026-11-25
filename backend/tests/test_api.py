from __future__ import annotations

import time

import pytest

from .conftest import Stack, build_stack
from .fakes import FakeGateway

UNSET = object()
DEFAULT_PROMPT = "You are a test assistant."


def post_chat(
    client,
    *,
    session_id: str = "s-test",
    message: str = "Hello",
    system_prompt=UNSET,
    headers: dict[str, str] | None = None,
):
    payload: dict = {"session_id": session_id, "message": message}
    if system_prompt is not UNSET:
        payload["system_prompt"] = system_prompt
    return client.post("/chat", json=payload, headers=headers or {})


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health_returns_exact_required_shape(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "keys_configured": 2,
        "cache_enabled": True,
    }


def test_health_503_when_cache_not_ready(stack: Stack):
    stack.gateway.cache_enabled = False
    response = stack.client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"detail": "cache unavailable"}


def test_health_503_when_key_pool_incomplete(stack: Stack):
    stack.gateway.keys_configured = 1
    response = stack.client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"detail": "key pool unavailable"}


def test_health_503_when_database_is_unreachable(stack: Stack):
    class BrokenRepository:
        async def ping(self):
            raise RuntimeError("db down")

    stack.app.state.repository = BrokenRepository()
    response = stack.client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"detail": "database unavailable"}


# ---------------------------------------------------------------------------
# Chat success and metadata
# ---------------------------------------------------------------------------


def test_chat_success_contract(client):
    response = post_chat(
        client, session_id="s-shape", message="  What is 2 + 2?  "
    )
    assert response.status_code == 200

    body = response.json()
    assert set(body) == {"session_id", "reply", "metadata"}
    assert body["session_id"] == "s-shape"
    assert body["reply"] == "Echo: What is 2 + 2?"

    metadata = body["metadata"]
    assert metadata["resolution_source"] == "LIVE_INFERENCE"
    assert metadata["model"] == "gemini/gemini-3.5-flash-lite"
    assert isinstance(metadata["latency_ms"], int)
    assert metadata["latency_ms"] >= 1
    assert metadata["input_tokens"] > 0
    assert metadata["output_tokens"] > 0
    assert metadata["key_id"] == "key_1"
    assert metadata["fallback_attempts"] == 0


def test_first_messages_of_equal_length_report_equal_input_tokens(client):
    first = post_chat(client, session_id="s-tokens-a", message="Hello there")
    second = post_chat(client, session_id="s-tokens-b", message="Hello there")

    assert first.status_code == second.status_code == 200
    assert (
        first.json()["metadata"]["input_tokens"]
        == second.json()["metadata"]["input_tokens"]
    )


def test_follow_up_includes_history_in_input_tokens(client):
    first = post_chat(client, session_id="s-tokens-history", message="Hello")
    second = post_chat(
        client, session_id="s-tokens-history", message="Tell me more"
    )

    assert (
        second.json()["metadata"]["input_tokens"]
        > first.json()["metadata"]["input_tokens"]
    )


def test_generation_parameters_are_sent_to_provider(stack: Stack):
    post_chat(stack.client)
    call = stack.gateway.calls[-1]
    assert call["messages"][0]["content"] == DEFAULT_PROMPT


# ---------------------------------------------------------------------------
# Validation matrix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"message": "Hi"},
        {"session_id": "", "message": "Hi"},
        {"session_id": "   ", "message": "Hi"},
        {"session_id": "s" * 129, "message": "Hi"},
        {"session_id": "s-invalid", "message": ""},
        {"session_id": "s-invalid", "message": "   "},
        {"session_id": "s-invalid", "message": "x" * 4001},
        {
            "session_id": "s-invalid",
            "message": "Hi",
            "system_prompt": "x" * 4001,
        },
    ],
)
def test_invalid_chat_payloads_return_422_and_persist_nothing(client, payload):
    response = client.post("/chat", json=payload)
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")
    assert "detail" in response.json()

    session_id = payload.get("session_id")
    if isinstance(session_id, str) and session_id.strip():
        assert (
            client.get(f"/sessions/{session_id}/messages").status_code == 404
        )


def test_malformed_json_returns_json_422(client):
    response = client.post(
        "/chat",
        content=b'{"session_id": "s-broken", "message": ',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")
    assert "detail" in response.json()
    assert client.get("/sessions/s-broken/messages").status_code == 404


# ---------------------------------------------------------------------------
# History and multi-turn state
# ---------------------------------------------------------------------------


def test_unknown_session_history_returns_exact_404(client):
    response = client.get("/sessions/s-missing/messages")
    assert response.status_code == 404
    assert response.json() == {"detail": "session not found"}


def test_history_is_oldest_first_and_excludes_system_prompt(client):
    first = post_chat(
        client,
        session_id="s-history",
        message="First question",
        system_prompt="Secret system instructions",
    )
    second = post_chat(
        client, session_id="s-history", message="Second question"
    )

    response = client.get("/sessions/s-history/messages")
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "s-history"
    assert [message["role"] for message in body["messages"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert body["messages"][0] == {
        "role": "user",
        "content": "First question",
    }
    assert body["messages"][2] == {
        "role": "user",
        "content": "Second question",
    }
    assert body["messages"][1]["content"] == first.json()["reply"]
    assert body["messages"][3]["content"] == second.json()["reply"]
    assert "details" not in body
    assert all(
        message.get("metadata") is None
        for message in body["messages"]
        if message["role"] == "user"
    )

    assistant_metadata = body["messages"][1]["metadata"]
    assert assistant_metadata["resolution_source"] == "LIVE_INFERENCE"
    assert assistant_metadata["model"] == "gemini/gemini-3.5-flash-lite"
    assert assistant_metadata["key_id"] == "key_1"
    assert assistant_metadata["fallback_attempts"] == 0
    assert assistant_metadata["input_tokens"] > 0
    assert assistant_metadata["output_tokens"] > 0
    assert assistant_metadata["latency_ms"] >= 1
    assert not any(
        message["content"] == "Secret system instructions"
        for message in body["messages"]
    )


def test_session_history_matches_stored_turns(stack: Stack):
    first = post_chat(stack.client, session_id="s-match", message="One")
    second = post_chat(stack.client, session_id="s-match", message="Two")

    history = stack.client.get("/sessions/s-match/messages").json()["messages"]
    assert history[1]["content"] == first.json()["reply"]
    assert history[3]["content"] == second.json()["reply"]


def test_multi_turn_history_is_sent_back_to_the_model(stack: Stack):
    first = post_chat(
        stack.client, session_id="s-multi", message="My name is Ada."
    )
    post_chat(stack.client, session_id="s-multi", message="What is my name?")

    second_call_messages = stack.gateway.calls[1]["messages"]
    assert second_call_messages[0] == {
        "role": "system",
        "content": DEFAULT_PROMPT,
    }
    assert second_call_messages[1] == {
        "role": "user",
        "content": "My name is Ada.",
    }
    assert second_call_messages[2] == {
        "role": "assistant",
        "content": first.json()["reply"],
    }
    assert second_call_messages[3] == {
        "role": "user",
        "content": "What is my name?",
    }


def test_sessions_are_isolated(stack: Stack):
    post_chat(stack.client, session_id="s-a", message="Only in A")
    post_chat(stack.client, session_id="s-a", message="Still A")
    post_chat(stack.client, session_id="s-b", message="Only in B")

    last_messages = stack.gateway.calls[-1]["messages"]
    assert len(last_messages) == 2
    assert last_messages[1] == {"role": "user", "content": "Only in B"}

    history_a = stack.client.get("/sessions/s-a/messages").json()["messages"]
    history_b = stack.client.get("/sessions/s-b/messages").json()["messages"]
    assert len(history_a) == 4
    assert len(history_b) == 2
    assert all("Only in B" not in m["content"] for m in history_a)


# ---------------------------------------------------------------------------
# System prompt semantics
# ---------------------------------------------------------------------------


def test_non_empty_system_prompt_overrides_and_persists(stack: Stack):
    post_chat(
        stack.client,
        session_id="s-prompt",
        message="Hi",
        system_prompt="Answer like a pirate.",
    )
    assert (
        stack.gateway.calls[-1]["messages"][0]["content"]
        == "Answer like a pirate."
    )

    post_chat(stack.client, session_id="s-prompt", message="Again")
    assert (
        stack.gateway.calls[-1]["messages"][0]["content"]
        == "Answer like a pirate."
    )


def test_empty_system_prompt_resets_to_default(stack: Stack):
    post_chat(
        stack.client,
        session_id="s-reset",
        message="Hi",
        system_prompt="Use bullet points.",
    )
    post_chat(
        stack.client,
        session_id="s-reset",
        message="Again",
        system_prompt="   ",
    )
    assert (
        stack.gateway.calls[-1]["messages"][0]["content"] == DEFAULT_PROMPT
    )


def test_failed_request_does_not_change_stored_prompt(stack: Stack):
    post_chat(
        stack.client,
        session_id="s-prompt-fail",
        message="Hi",
        system_prompt="Keep this prompt.",
    )
    failed = post_chat(
        stack.client,
        session_id="s-prompt-fail",
        message="Change it",
        system_prompt="Should never persist.",
        headers={"X-Simulate-Failure": "*=429"},
    )
    assert failed.status_code == 503

    post_chat(stack.client, session_id="s-prompt-fail", message="Next")
    assert (
        stack.gateway.calls[-1]["messages"][0]["content"] == "Keep this prompt."
    )


# ---------------------------------------------------------------------------
# Failure simulation matrix
# ---------------------------------------------------------------------------


def test_simulated_rate_limit_returns_real_answer_from_second_key(client):
    response = post_chat(
        client,
        session_id="s-failover-429",
        message="Explain failover.",
        headers={"X-Simulate-Failure": "key_1=429"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Echo: Explain failover."
    assert body["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert body["metadata"]["key_id"] == "key_2"
    assert body["metadata"]["fallback_attempts"] == 1


def test_simulated_500_returns_real_answer_from_second_key(client):
    response = post_chat(
        client,
        session_id="s-failover-500",
        message="Explain failover.",
        headers={"X-Simulate-Failure": "key_1=500"},
    )
    assert response.status_code == 200
    assert response.json()["metadata"]["key_id"] == "key_2"
    assert response.json()["metadata"]["fallback_attempts"] == 1


@pytest.mark.parametrize(
    "header",
    ["key_1=429,key_2=500", "*=429", "*=500", "*=503"],
)
def test_all_keys_simulated_failing_returns_exact_503(client, header):
    response = post_chat(
        client,
        session_id="s-all-fail",
        message="This must not persist.",
        headers={"X-Simulate-Failure": header},
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "all providers unavailable"}
    assert client.get("/sessions/s-all-fail/messages").status_code == 404


def test_malformed_simulation_header_is_ignored(client):
    response = post_chat(
        client,
        session_id="s-malformed-sim",
        message="Hello",
        headers={"X-Simulate-Failure": "nonsense,key_9=429,key_1=999"},
    )
    assert response.status_code == 200
    assert response.json()["metadata"]["key_id"] == "key_1"
    assert response.json()["metadata"]["fallback_attempts"] == 0


def test_simulation_header_is_ignored_when_disabled(tmp_path):
    with build_stack(tmp_path, enable_failure_simulation=False) as stack:
        response = post_chat(
            stack.client,
            session_id="s-disabled",
            message="Hello",
            headers={"X-Simulate-Failure": "*=429"},
        )
        assert response.status_code == 200
        assert response.json()["metadata"]["key_id"] == "key_1"
        assert response.json()["metadata"]["fallback_attempts"] == 0


def test_simulated_failure_bypasses_prewarmed_cache(stack: Stack):
    prewarm = post_chat(
        stack.client,
        session_id="s-prewarm",
        message="A cacheable question",
    )
    assert prewarm.status_code == 200
    assert prewarm.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"

    simulated = post_chat(
        stack.client,
        session_id="s-prewarm-sim",
        message="A cacheable question",
        headers={"X-Simulate-Failure": "key_1=429"},
    )
    assert simulated.status_code == 200
    metadata = simulated.json()["metadata"]
    assert metadata["resolution_source"] == "LIVE_INFERENCE"
    assert metadata["key_id"] == "key_2"
    assert metadata["fallback_attempts"] == 1


def test_wildcard_simulation_after_prewarm_still_returns_503(stack: Stack):
    post_chat(
        stack.client, session_id="s-prewarm-503", message="Cached question"
    )
    response = post_chat(
        stack.client,
        session_id="s-prewarm-503-b",
        message="Cached question",
        headers={"X-Simulate-Failure": "*=429"},
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "all providers unavailable"}


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------


def test_repeated_first_message_across_sessions_is_cache_hit(client):
    first = post_chat(
        client,
        session_id="s-cache-a",
        message="What is the capital of France?",
    )
    second = post_chat(
        client,
        session_id="s-cache-b",
        message="What is the capital of France?",
    )

    assert first.status_code == second.status_code == 200
    first_body = first.json()
    second_body = second.json()

    assert first_body["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert first_body["metadata"]["key_id"] == "key_1"

    assert second_body["metadata"]["resolution_source"] == "LLM_CACHE"
    assert second_body["reply"] == first_body["reply"]
    assert second_body["metadata"]["key_id"] is None
    assert second_body["metadata"]["fallback_attempts"] == 0
    assert (
        second_body["metadata"]["input_tokens"]
        == first_body["metadata"]["input_tokens"]
    )
    assert (
        second_body["metadata"]["output_tokens"]
        == first_body["metadata"]["output_tokens"]
    )


def test_different_message_is_never_served_from_cache(client):
    first = post_chat(
        client, session_id="s-cache-diff-a", message="Question one"
    )
    second = post_chat(
        client, session_id="s-cache-diff-b", message="Question two"
    )
    assert first.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert second.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert second.json()["reply"] != first.json()["reply"]


def test_changed_system_prompt_forces_cache_miss(client):
    first = post_chat(
        client,
        session_id="s-cache-prompt-a",
        message="Same question",
        system_prompt="Answer briefly.",
    )
    second = post_chat(
        client,
        session_id="s-cache-prompt-b",
        message="Same question",
        system_prompt="Answer in detail.",
    )
    assert first.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert second.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"


def test_cache_hit_is_faster_than_live_inference(tmp_path):
    with build_stack(tmp_path, live_delay=0.2) as stack:
        started = time.perf_counter()
        first = post_chat(
            stack.client, session_id="s-fast-a", message="Speed test"
        )
        live_elapsed = time.perf_counter() - started

        started = time.perf_counter()
        second = post_chat(
            stack.client, session_id="s-fast-b", message="Speed test"
        )
        cached_elapsed = time.perf_counter() - started

        assert first.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
        assert second.json()["metadata"]["resolution_source"] == "LLM_CACHE"
        assert cached_elapsed < live_elapsed


def test_tokens_are_per_request_not_conversation_totals(client):
    first = post_chat(client, session_id="s-per-request", message="First")
    second = post_chat(client, session_id="s-per-request", message="Second")

    first_output = first.json()["metadata"]["output_tokens"]
    second_output = second.json()["metadata"]["output_tokens"]
    # Both replies are "Echo: <message>" of comparable length; the second is
    # not a running sum of both completions.
    assert second_output < first_output + second_output
    assert second_output == max(1, len("Echo: Second") // 4)


# ---------------------------------------------------------------------------
# HTTP surface, CORS and error shape
# ---------------------------------------------------------------------------


def test_generated_docs_are_disabled(client):
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_cors_preflight_allows_frontend_and_simulation_header(client):
    response = client.options(
        "/chat",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-simulate-failure",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:3000"
    )
    allowed_headers = response.headers["access-control-allow-headers"].lower()
    assert "x-simulate-failure" in allowed_headers
    assert "content-type" in allowed_headers


def test_cors_rejects_unlisted_origin(client):
    response = client.options(
        "/chat",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_unexpected_error_is_json_without_details(tmp_path):
    class ExplodingGateway(FakeGateway):
        async def complete(self, messages, simulation):
            raise RuntimeError("secret internal detail")

    with build_stack(
        tmp_path,
        gateway_factory=ExplodingGateway,
        raise_server_exceptions=False,
    ) as stack:
        response = post_chat(stack.client, session_id="s-500", message="Boom")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "internal server error"}
    assert "secret internal detail" not in response.text


def test_404_unknown_route_is_json(client):
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert "detail" in response.json()
