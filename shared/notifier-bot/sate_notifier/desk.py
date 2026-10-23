"""Figures the bot may show. Unloaded fields stay unknown."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DeskView:
    mode: str = ""
    halt_level: str = "unknown"
    kill_state: str = "unknown"
    halt_command: str = ""
    partial_halt: bool = False
    heartbeat_ok: bool | None = None
    feed_latency_ms: str = "unknown"
    cash_floor: str = "unknown"
    obligations: str = "unknown"
    reimbursement_state: str = "unknown"
    equity_a: str = "unknown"
    equity_b: str = "unknown"
    positions_loaded: bool = False
    positions: tuple[str, ...] = ()
    mask_amounts: bool = False
