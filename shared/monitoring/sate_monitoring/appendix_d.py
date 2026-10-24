"""Appendix D hooks: market data and news licence compliance (**Phase 19**)."""

from __future__ import annotations

from datetime import UTC, datetime


def _entry(
    assumption_id: str,
    assumption: str,
    verification_method: str,
    *,
    vendor: str,
    verified_at: str | None = None,
) -> dict[str, str]:
    when = verified_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "assumption_id": assumption_id,
        "assumption": assumption,
        "verification_method": verification_method,
        "verified_at": when,
        "vendor": vendor,
        "gate_blocked_if_stale": "true",
    }


def market_data_licence(*, vendor: str, verified_at: str | None = None) -> dict[str, str]:
    if not vendor.strip():
        raise ValueError("vendor is required")
    return _entry(
        "APP-D-DATA-01",
        "Market data redistribution complies with vendor terms for SIM and LIVE",
        "Owner attestation + terms URL retained by reference in fact log",
        vendor=vendor,
        verified_at=verified_at,
    )


def news_licence(*, vendor: str, verified_at: str | None = None) -> dict[str, str]:
    if not vendor.strip():
        raise ValueError("vendor is required")
    return _entry(
        "APP-D-NEWS-01",
        "News and calendar feeds used only within licensed scope",
        "Blackout rules tested in kernel; licence expiry monitored",
        vendor=vendor,
        verified_at=verified_at,
    )
