"""BAT protective-order steps on the demo bridge."""

from __future__ import annotations

from sate_mt5_bridge.bridge import Bridge
from sate_mt5_bridge.errors import AdapterError


def run_protective_order_bat(
    bridge: Bridge,
    *,
    login: str,
    server: str,
    grant: dict[str, object],
    instrument: str,
    stop: str,
) -> list[str]:
    steps: list[str] = []
    bridge.connect(login, server, grant, instrument=instrument)
    order = bridge.place_placeholder(
        verdict="Allow",
        idempotency_key="bat-stop-1",
        instrument=instrument,
        side="BUY",
        quantity="1",
        reduce_only=False,
        protective_stop=stop,
    )
    if not order.stop_attached:
        raise AdapterError("BAT stop attachment failed", code="protective_stop")
    steps.append("place_market_with_stop")
    steps.append("broker_ack_stop_attached")
    try:
        bridge.place_placeholder(
            verdict="Allow",
            idempotency_key="bat-no-stop",
            instrument=instrument,
            side="BUY",
            quantity="1",
            reduce_only=False,
            protective_stop="",
        )
    except AdapterError:
        steps.append("reject_entry_without_stop")
    return steps
