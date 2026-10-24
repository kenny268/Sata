"""Fact-log writer for LIVE-L1 transitions."""

from __future__ import annotations

from sate_factlog.log import FactLog

WRITER_ID = "live-l1-a"


def persist_mode_transition(
    log: FactLog,
    *,
    from_mode: str,
    to_mode: str,
    at: str,
    correlation_id: str = "sim-to-live-c4",
) -> None:
    log.append(
        event_id=f"mode-{from_mode}-to-{to_mode}-{at}",
        event_type="deployment",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id=correlation_id,
        writer_id=WRITER_ID,
        payload={
            "kind": "mode_transition",
            "from_mode": from_mode,
            "to_mode": to_mode,
            "preflight_required": True,
        },
    )


def persist_ramp_started(log: FactLog, *, ramp_factor: str, started_at: str) -> None:
    log.append(
        event_id=f"ramp-start-{started_at}",
        event_type="deployment",
        group_scope="A",
        occurred_at=started_at,
        recorded_at=started_at,
        correlation_id="sim-to-live-c4",
        writer_id=WRITER_ID,
        payload={
            "kind": "ramp_clock_started",
            "ramp_factor": ramp_factor,
            "min_days": 30,
            "quiet_period": True,
        },
    )


def persist_safe_window(log: FactLog, *, scheduled_at: str) -> None:
    log.append(
        event_id=f"safe-window-{scheduled_at}",
        event_type="deployment",
        group_scope="A",
        occurred_at=scheduled_at,
        recorded_at=scheduled_at,
        correlation_id="sim-to-live-c4",
        writer_id=WRITER_ID,
        payload={"kind": "safe_window_scheduled", "flat_required": True},
    )
