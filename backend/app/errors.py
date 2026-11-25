"""Domain errors shared by the gateway, service and API layers."""

from __future__ import annotations


class AllProvidersUnavailable(Exception):
    """Raised when every key in the pool failed for a single request."""


class SessionNotFound(Exception):
    """Raised when a session history lookup targets an unknown session."""
