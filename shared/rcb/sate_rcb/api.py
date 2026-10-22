"""POST /capital/ratify. Passkey presence is a stub until Phase 16."""

from __future__ import annotations

from sate_factlog.log import FactLog

from sate_rcb.errors import RcbError
from sate_rcb.service import RcbState
from sate_rcb.sourced import submit_ratify

_SCOPES = frozenset({"A", "B"})


def post_capital_ratify(
    log: FactLog,
    state: RcbState,
    *,
    scope: str,
    passkey_assertion: str,
    now: str,
    event_id: str,
    recorded_at: str,
    correlation_id: str,
) -> RcbState:
    """Owner ratification. The service does not supply the passkey itself."""
    if scope not in _SCOPES:
        raise RcbError(f"explicit group scope required, got {scope!r}", code="scope")
    if state.group_scope != scope:
        raise RcbError("RCB scope does not match the request", code="scope")
    return submit_ratify(
        log,
        state,
        passkey_assertion=passkey_assertion,
        ratified_at=now,
        event_id=event_id,
        recorded_at=recorded_at,
        correlation_id=correlation_id,
    )
