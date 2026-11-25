"""Shared pytest fixtures: isolated SQLite file, fake gateway and test client."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import create_app
from app.config import Settings

from .fakes import FakeGateway

TEST_KEYS = "test-key-alpha,test-key-beta"


def make_settings(tmp_path: Path, **overrides) -> Settings:
    values = {
        "llm_api_keys": TEST_KEYS,
        "llm_model": "gemini/gemini-3.5-flash-lite",
        "database_url": f"sqlite:///{tmp_path / 'app.db'}",
        "allowed_origins": "http://localhost:3000",
        "enable_failure_simulation": True,
        "default_system_prompt": "You are a test assistant.",
        "cache_ttl_seconds": 3600,
        "log_level": "WARNING",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@dataclass
class Stack:
    settings: Settings
    gateway: FakeGateway
    app: FastAPI
    client: TestClient


@contextmanager
def build_stack(
    tmp_path: Path,
    *,
    gateway: FakeGateway | None = None,
    gateway_factory: Callable[[Settings], FakeGateway] | None = None,
    live_delay: float = 0.0,
    raise_server_exceptions: bool = True,
    **setting_overrides,
) -> Iterator[Stack]:
    settings = make_settings(tmp_path, **setting_overrides)
    if gateway is None and gateway_factory is not None:
        gateway = gateway_factory(settings)
    active_gateway = gateway or FakeGateway(settings, live_delay=live_delay)
    app = create_app(settings=settings, gateway=active_gateway)
    with TestClient(
        app, raise_server_exceptions=raise_server_exceptions
    ) as client:
        yield Stack(
            settings=settings,
            gateway=active_gateway,
            app=app,
            client=client,
        )


@pytest.fixture
def stack(tmp_path: Path) -> Iterator[Stack]:
    with build_stack(tmp_path) as active_stack:
        yield active_stack


@pytest.fixture
def client(stack: Stack) -> TestClient:
    return stack.client


@pytest.fixture
def stack_factory(tmp_path: Path):
    @contextmanager
    def _factory(**overrides) -> Iterator[Stack]:
        with build_stack(tmp_path, **overrides) as active_stack:
            yield active_stack

    return _factory
