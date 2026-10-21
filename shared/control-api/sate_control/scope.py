"""Group scope gate. Phase 1 governance hook for A-IND-02.

Combined and GLOBAL scopes are rejected. Risk and control calls name one group.
"""

from __future__ import annotations

ALLOWED = frozenset({"A", "B"})


def require_scope(scope: str) -> str:
    if scope not in ALLOWED:
        raise ValueError(f"explicit group scope required, got {scope!r}")
    return scope
