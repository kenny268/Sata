"""Appendix C **C.4** SIM→LIVE runbook steps."""

from __future__ import annotations

C4_STEPS = (
    "preflight_and_evidence",
    "web_passkey_arm",
    "arming_delay_24h",
    "telegram_otp_web_confirm",
    "safe_window",
    "ramp_and_shadow_twin",
    "first_live_session_recon",
)


def runbook_export() -> dict[str, object]:
    return {
        "runbook": "C.4",
        "title": "SIM to LIVE",
        "steps": list(C4_STEPS),
        "am_ids": ["AM-01", "AM-A1"],
        "oi_tg_01": "otp_via_telegram_entered_in_web_only",
    }
