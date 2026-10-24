"""Run MT5 demo BAT and map into compliance protective-order gate."""

from __future__ import annotations

from sate_compliance.bat_protective import ProtectiveOrderBat

try:
    from sate_mt5_bridge.bat import run_protective_order_bat
except ImportError:  # pragma: no cover - optional PYTHONPATH
    run_protective_order_bat = None  # type: ignore[misc, assignment]


def run_demo_protective_bat(bridge: object, *, stop: str = "1.0700") -> ProtectiveOrderBat:
    if run_protective_order_bat is None:
        raise RuntimeError("sate_mt5_bridge is not on PYTHONPATH")
    bat = ProtectiveOrderBat()
    steps = run_protective_order_bat(
        bridge,  # type: ignore[arg-type]
        login="10001",
        server="Exness-MT5Trial",
        grant={"group": "A", "injected": True},
        instrument="EURUSD",
        stop=stop,
    )
    bat.steps.extend(steps)
    return bat
