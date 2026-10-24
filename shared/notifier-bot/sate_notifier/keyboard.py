"""Persistent reply keyboard (**TG-PO-02**, TG-T-09)."""

from __future__ import annotations

REPLY_KEYBOARD = [
    ["Status", "Positions", "P&L"],
    ["Controls", "Treasury", "Help"],
]

BUTTON_COMMANDS = {
    "status": "/status",
    "positions": "/positions",
    "p&l": "/pnl",
    "controls": "/controls",
    "treasury": "/treasury",
    "help": "/help",
}


def button_to_command(label: str) -> str:
    return BUTTON_COMMANDS.get(label.strip().lower(), "")
