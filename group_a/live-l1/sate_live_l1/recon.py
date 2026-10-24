"""Post-session reconciliation audit (Phase 26 mandatory)."""

from __future__ import annotations

from sate_factlog.log import FactLog

from sate_live_l1.persist import WRITER_ID


def persist_post_session_recon(
    log: FactLog,
    *,
    session_id: str,
    clean: bool,
    stops_verified: bool,
    at: str,
) -> None:
    log.append(
        event_id=f"live-recon-{session_id}",
        event_type="deployment",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id=session_id,
        writer_id=WRITER_ID,
        payload={
            "kind": "live_post_session_recon",
            "as_of": at,
            "action": "recon_clean" if clean else "recon_mismatch",
            "stops_verified_on_broker": stops_verified,
            "mandatory": True,
        },
    )
