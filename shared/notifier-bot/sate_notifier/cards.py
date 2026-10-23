"""Read-only cards. Combined P&L is labelled and never added (**TG-14**)."""

from __future__ import annotations

import re

from sate_notifier.desk import DeskView
from sate_notifier.tags import COMBINED_LABEL, halt_line, scope_tag

_AMOUNT = re.compile(r"\d")


def status_card(desk: DeskView) -> str:
    tag = scope_tag("A", desk.mode)
    halt = halt_line(desk.halt_command, partial_halt=desk.partial_halt)
    lines = [
        f"{tag} SYSTEM INFO",
        f"Mode: {desk.mode or 'unknown'}",
        f"Halt level: {desk.halt_level}",
        f"Kill: {desk.kill_state}",
    ]
    if halt:
        lines.append(halt)
    return _mask("\n".join(lines), desk.mask_amounts)


def positions_card(desk: DeskView) -> str:
    tag = scope_tag("A", desk.mode)
    if not desk.positions_loaded:
        body = f"{tag} TRADE INFO\nPositions unloaded."
    elif not desk.positions:
        body = f"{tag} TRADE INFO\nNo open positions."
    else:
        rows = "\n".join(f"- {row}" for row in desk.positions)
        body = f"{tag} TRADE INFO\n{rows}"
    return _mask(body, desk.mask_amounts)


def pnl_card(desk: DeskView) -> str:
    tag = scope_tag("ALL", desk.mode)
    body = (
        f"{tag} SUMMARY INFO\n"
        f"Group A equity: {desk.equity_a}\n"
        f"Group B equity: {desk.equity_b}\n"
        f"{COMBINED_LABEL}"
    )
    return _mask(body, desk.mask_amounts)


def otp_notice(*, code: str, mode: str = "SIM") -> dict[str, object]:
    """SIM→LIVE code is delivered here and confirmed only on the web (**TG-16**)."""
    tag = scope_tag("A", mode)
    return {
        "text": (
            f"{tag} MODE WARN\n"
            "SIM to LIVE code. Enter it only in the web app.\n"
            f"{code}"
        ),
        "buttons": [],
        "web_entry_only": True,
    }


def _mask(body: str, enabled: bool) -> str:
    if not enabled:
        return body
    return _AMOUNT.sub("•", body)
