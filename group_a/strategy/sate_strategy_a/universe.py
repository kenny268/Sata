"""Universe rules **A-UNI-01–03**."""

from __future__ import annotations

LIVE_L1 = frozenset({"EURUSD"})


def allowed_instruments(*, account_mode: str, rung: str) -> frozenset[str]:
    if account_mode not in {"SIM", "LIVE"}:
        raise ValueError("account_mode must be SIM or LIVE")
    if rung == "LIVE-L1" or (account_mode == "LIVE" and rung.startswith("LIVE-L1")):
        return LIVE_L1
    if account_mode == "SIM":
        return frozenset({"EURUSD", "XAUUSD", "BTCUSD"})
    return LIVE_L1


def validate_instrument(instrument: str, *, account_mode: str, rung: str) -> None:
    if instrument not in allowed_instruments(account_mode=account_mode, rung=rung):
        raise ValueError(f"{instrument} is not in the universe for {account_mode}/{rung}")
