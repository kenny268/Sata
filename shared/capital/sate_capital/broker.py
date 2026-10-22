"""Mock broker adapter. Posts a deposit and the broker snapshot that follows it."""

from __future__ import annotations

from sate_factlog.log import FactLog

from sate_capital.ledger import CapitalState
from sate_capital.sourced import submit_deposit, submit_snapshot


def mock_deposit(
    log: FactLog,
    state: CapitalState,
    *,
    amount: str,
    halted: bool,
    reported: dict[str, str],
    event_id: str,
    occurred_at: str,
    recorded_at: str,
    correlation_id: str,
) -> CapitalState:
    """Record the deposit, then the broker's following snapshot. The base is not raised."""
    identity = {
        "occurred_at": occurred_at,
        "recorded_at": recorded_at,
        "correlation_id": correlation_id,
    }
    state = submit_deposit(
        log,
        state,
        {"amount": amount, "currency": state.currency, "halted": halted},
        event_id=f"{event_id}-deposit",
        **identity,
    )
    return submit_snapshot(
        log,
        state,
        reported,
        event_id=f"{event_id}-snapshot",
        **identity,
    )
