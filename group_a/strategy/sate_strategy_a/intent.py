"""Execution intent builder and schema validation (**§6.2**)."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

_SCHEMA = json.loads(
    (Path(__file__).resolve().parents[3] / "shared" / "schemas" / "intent.schema.json").read_text(encoding="utf-8")
)


def build_intent(
    *,
    intent_id: str,
    account_mode: str,
    instrument: str,
    side: str,
    quantity: str,
    protective_stop: str,
    strategy_id: str,
    created_at: str,
    signal_refs: list[str] | None = None,
    advisory_refs: list[str] | None = None,
    slippage_budget: str | None = "0.5",
) -> dict[str, object]:
    intent: dict[str, object] = {
        "intent_id": intent_id,
        "trace_id": intent_id,
        "group": "A",
        "account_mode": account_mode,
        "instrument": instrument,
        "side": side,
        "quantity": quantity,
        "order_type": "MARKET",
        "limit_price": None,
        "protective_stop": protective_stop,
        "take_profit": None,
        "slippage_budget": slippage_budget,
        "strategy_id": strategy_id,
        "signal_refs": signal_refs or [],
        "advisory_refs": advisory_refs or [],
        "created_at": created_at,
    }
    validate_intent(intent)
    return intent


def validate_intent(intent: dict[str, object]) -> None:
    jsonschema.validate(intent, _SCHEMA)
