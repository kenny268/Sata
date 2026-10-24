"""Shadow twin (**A-SWT-03**)."""

from __future__ import annotations

from sate_factlog.log import FactLog

from sate_live_l1.persist import WRITER_ID


def start_shadow_twin(log: FactLog, *, live_session_id: str, at: str) -> str:
    twin_id = f"shadow-{live_session_id}"
    log.append(
        event_id=f"shadow-twin-{live_session_id}",
        event_type="deployment",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id=live_session_id,
        writer_id=WRITER_ID,
        payload={
            "kind": "shadow_twin_started",
            "live_session_id": live_session_id,
            "twin_session_id": twin_id,
            "account_mode_live": "LIVE-L1",
            "account_mode_twin": "SIM",
        },
    )
    return twin_id
