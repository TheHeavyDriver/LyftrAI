"""Deterministic LiteLLM response-cache keys.

The key intentionally excludes API keys, key ids, session ids and simulation
state. Two identical first messages in different sessions therefore share a
cache entry, while a changed message, history turn, system prompt, model or
generation parameter cannot collide.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

CACHE_KEY_PREFIX = "lyftr:v1:"


def build_cache_key(
    *,
    model: str,
    messages: Sequence[dict[str, Any]],
    temperature: float,
    max_output_tokens: int,
) -> str:
    payload = {
        "model": model,
        "messages": list(messages),
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
    }
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return f"{CACHE_KEY_PREFIX}{digest}"
