"""Parsing for the request-scoped ``X-Simulate-Failure`` evaluation hook."""

from __future__ import annotations

from collections.abc import Iterable

ALLOWED_SIMULATED_STATUSES = frozenset({429, 500, 502, 503})


def parse_simulation_header(
    header_value: str | None,
    *,
    key_ids: Iterable[str],
    enabled: bool,
) -> dict[str, int]:
    """Return a request-scoped mapping of key id to simulated HTTP status.

    Unknown key ids, malformed pairs and unsupported status codes are ignored.
    ``*`` expands to every configured key. Later directives win. When the
    feature flag is off, the header is ignored completely.
    """

    if not enabled or not header_value:
        return {}

    known_ids = set(key_ids)
    simulated: dict[str, int] = {}

    for raw_pair in header_value.split(","):
        pair = raw_pair.strip()
        if not pair or "=" not in pair:
            continue

        raw_key, raw_status = pair.split("=", 1)
        key = raw_key.strip()
        status_text = raw_status.strip()

        if not key or not status_text:
            continue

        try:
            status = int(status_text)
        except ValueError:
            continue

        if status not in ALLOWED_SIMULATED_STATUSES:
            continue

        if key == "*":
            for key_id in known_ids:
                simulated[key_id] = status
        elif key in known_ids:
            simulated[key] = status

    return simulated
