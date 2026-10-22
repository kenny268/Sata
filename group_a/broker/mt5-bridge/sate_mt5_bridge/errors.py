"""Adapter failures. A disconnect does not become a second order."""

from __future__ import annotations


class AdapterError(ValueError):
    """The terminal call cannot proceed."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code
