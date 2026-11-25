from __future__ import annotations

from pathlib import Path

from .conftest import build_stack
from .test_api import post_chat


def test_history_survives_app_recreation(tmp_path: Path):
    with build_stack(tmp_path) as first:
        response = post_chat(
            first.client,
            session_id="s-persist",
            message="Remember this question",
        )
        assert response.status_code == 200
        expected_reply = response.json()["reply"]
        expected_metadata = response.json()["metadata"]

    database_file = tmp_path / "app.db"
    assert database_file.exists()

    with build_stack(tmp_path) as second:
        history_response = second.client.get("/sessions/s-persist/messages")
        assert history_response.status_code == 200
        messages = history_response.json()["messages"]

        assert len(messages) == 2
        assert messages[0] == {
            "role": "user",
            "content": "Remember this question",
        }
        assert messages[1]["content"] == expected_reply
        assert messages[1]["metadata"] == expected_metadata

        # A new process has a new in-memory cache, so the same first message
        # is generated live again.
        repeated = post_chat(
            second.client,
            session_id="s-persist-new",
            message="Remember this question",
        )
        assert (
            repeated.json()["metadata"]["resolution_source"]
            == "LIVE_INFERENCE"
        )


def test_schema_is_created_automatically_on_empty_database(tmp_path: Path):
    database_file = tmp_path / "app.db"
    assert not database_file.exists()

    with build_stack(tmp_path) as stack:
        assert database_file.exists()
        assert stack.client.get("/health").status_code == 200
        assert stack.client.get("/sessions/anything/messages").status_code == 404


def test_failed_request_does_not_create_a_session_or_messages(tmp_path: Path):
    with build_stack(tmp_path) as stack:
        response = post_chat(
            stack.client,
            session_id="s-failed-persist",
            message="Do not store me",
            headers={"X-Simulate-Failure": "*=429"},
        )
        assert response.status_code == 503
        assert (
            stack.client.get("/sessions/s-failed-persist/messages").status_code
            == 404
        )

        # The session starts clean, not with a half turn.
        success = post_chat(
            stack.client, session_id="s-failed-persist", message="Now store me"
        )
        assert success.status_code == 200
        history = stack.client.get(
            "/sessions/s-failed-persist/messages"
        ).json()["messages"]
        assert len(history) == 2
        assert history[0]["content"] == "Now store me"


def test_stored_system_prompt_survives_restart(tmp_path: Path):
    with build_stack(tmp_path) as first:
        post_chat(
            first.client,
            session_id="s-prompt-persist",
            message="Hello",
            system_prompt="Persist this instruction.",
        )

    with build_stack(tmp_path) as second:
        post_chat(
            second.client, session_id="s-prompt-persist", message="Follow up"
        )
        last_call = second.gateway.calls[-1]
        assert last_call["messages"][0]["content"] == (
            "Persist this instruction."
        )
        assert last_call["messages"][1]["content"] == "Hello"


def test_cache_is_process_local_and_resets_after_restart(tmp_path: Path):
    with build_stack(tmp_path) as first:
        post_chat(first.client, session_id="s-cache-1", message="Cache me")
        cached = post_chat(
            first.client, session_id="s-cache-2", message="Cache me"
        )
        assert cached.json()["metadata"]["resolution_source"] == "LLM_CACHE"

    with build_stack(tmp_path) as second:
        after_restart = post_chat(
            second.client, session_id="s-cache-3", message="Cache me"
        )
        assert (
            after_restart.json()["metadata"]["resolution_source"]
            == "LIVE_INFERENCE"
        )
