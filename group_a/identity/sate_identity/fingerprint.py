"""Account number plus server. A-MOD-02 fields, without the later halt action."""

from __future__ import annotations

from dataclasses import dataclass

from sate_identity.errors import IsolationError

PROFILES = {"A-SIM": "SIM", "A-LIVE": "LIVE"}


@dataclass(frozen=True)
class Fingerprint:
    account_login: str
    server: str

    def matches(self, other: Fingerprint) -> bool:
        return self.account_login == other.account_login and self.server == other.server


def parse_fingerprint(account_login: str, server: str) -> Fingerprint:
    login = account_login.strip()
    host = server.strip()
    if not login or any(ch.isspace() for ch in login):
        raise IsolationError("account login is required and cannot contain whitespace")
    if not host or any(ch.isspace() for ch in host):
        raise IsolationError("broker server is required and cannot contain whitespace")
    return Fingerprint(account_login=login, server=host)


def require_profile(profile_id: str) -> str:
    if profile_id not in PROFILES:
        raise IsolationError(f"unknown Group A profile {profile_id!r}")
    return PROFILES[profile_id]
