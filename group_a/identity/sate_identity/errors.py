"""Failures that would mix Group A state with another scope."""


class IsolationError(ValueError):
    """Raised when a write is not strictly group A."""
