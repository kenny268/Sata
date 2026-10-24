"""Command parser and reduce-only policy (**TG-T-07**, **TG-09**)."""

from __future__ import annotations

WEB_ONLY = "Open the web control plane with passkey to continue."

_FORBIDDEN = frozenset({"/resume", "/live", "/loosen", "/constitution", "/edit"})
_REDUCE = frozenset({"/halt", "/flatten", "/kill", "/mode", "/alive", "/controls"})


def parse_command(text: str) -> str:
    token = text.strip().split()[0].lower() if text.strip() else ""
    if not token.startswith("/"):
        return ""
    return token.split("@", 1)[0]


def classify_command(command: str) -> dict[str, str]:
    if command in _FORBIDDEN or command.startswith("/live"):
        return {"class": "abstain", "channel": "web_only", "message": WEB_ONLY}
    if command in _REDUCE or command.startswith("/mode"):
        return {"class": "reduce", "channel": "telegram"}
    if command in {"/status", "/positions", "/pnl", "/risk", "/health", "/digest", "/why", "/help"}:
        return {"class": "read", "channel": "telegram"}
    if command == "/mute":
        return {"class": "neutral", "channel": "telegram"}
    return {"class": "unknown", "channel": "telegram"}
