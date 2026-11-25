"""Uvicorn entrypoint.

Run exactly one worker: LiteLLM's in-memory cache and the per-session locks are
process-local, and SQLite is the only permitted store.
"""

from __future__ import annotations

from .api import create_app

app = create_app()
