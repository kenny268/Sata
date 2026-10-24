"""Appendix D assumption register entry for the email transport."""

from __future__ import annotations

from datetime import UTC, datetime


def email_provider_assumption(*, transport: str, verified_at: str | None = None) -> dict[str, str]:
    if transport not in {"console", "smtp"}:
        raise ValueError("transport must be console or smtp")
    when = verified_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "assumption_id": "APP-D-EMAIL-01",
        "assumption": "Owner check-in reminders use the configured email transport",
        "verification_method": "SMTP integration test with mocked server; console in CI",
        "verified_at": when,
        "transport": transport,
        "gate_blocked_if_stale": "false",
    }
