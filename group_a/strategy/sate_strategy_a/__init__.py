"""Strategy boundary. Phase 1 builds an intent-shaped dict and does not send it."""

from __future__ import annotations


def stub_intent(*, intent_id: str, instrument: str) -> dict[str, object]:
    return {
        "intent_id": intent_id,
        "trace_id": intent_id,
        "group": "A",
        "account_mode": "SIM",
        "instrument": instrument,
        "side": "BUY",
        "quantity": "0",
        "order_type": "MARKET",
        "strategy_id": "phase-1-stub",
        "signal_refs": [],
        "advisory_refs": [],
        "created_at": "1970-01-01T00:00:00Z",
    }
