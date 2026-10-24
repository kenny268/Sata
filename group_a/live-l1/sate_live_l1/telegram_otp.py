"""Telegram OTP delivery (**OI-TG-01**, §4.3 step 4 — entry web-only)."""

from __future__ import annotations

from sate_factlog.log import FactLog

from sate_live_l1.persist import WRITER_ID


def deliver_arm_otp(log: FactLog, *, otp: str, at: str, channel: str = "telegram") -> None:
    log.append(
        event_id=f"live-arm-otp-{at}",
        event_type="deployment",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id="sim-to-live-c4",
        writer_id=WRITER_ID,
        payload={
            "kind": "oi_tg_01_arm_otp",
            "channel": channel,
            "otp_hash_prefix": otp[:2] + "****",
            "web_entry_only": True,
        },
    )
