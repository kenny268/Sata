"""Fact-log persistence for Phase 25 preflight evidence."""

from __future__ import annotations

from sate_factlog.log import FactLog

WRITER_ID = "live-readiness-a"


def persist_phase25_report(
    log: FactLog,
    *,
    event_id: str,
    report: dict[str, object],
    at: str,
) -> None:
    log.append(
        event_id=event_id,
        event_type="deployment",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id="live-readiness-phase25",
        writer_id=WRITER_ID,
        payload={"kind": "phase25_report", **report},
    )


def persist_rcb_floor_attestation(log: FactLog, *, at_or_above_floor: bool, at: str) -> None:
    log.append(
        event_id=f"live-rcb-floor-{at[:10]}",
        event_type="deployment",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id="live-readiness-phase25",
        writer_id=WRITER_ID,
        payload={"kind": "live_rcb_floor_attestation", "at_or_above_floor": at_or_above_floor},
    )


def persist_constitution_snapshot(
    log: FactLog,
    *,
    constitution: dict[str, object],
    at: str,
) -> None:
    log.append(
        event_id=f"live-constitution-{at[:10]}",
        event_type="deployment",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id="live-readiness-phase25",
        writer_id=WRITER_ID,
        payload={
            "kind": "live_constitution_snapshot",
            "meta": constitution.get("meta", {}),
            "risk": constitution.get("risk", {}),
            "mode": constitution.get("mode", {}),
        },
    )


def persist_design_review_gate(log: FactLog, *, complete: bool, at: str) -> None:
    log.append(
        event_id=f"live-design-review-{at[:10]}",
        event_type="deployment",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id="live-readiness-phase25",
        writer_id=WRITER_ID,
        payload={"kind": "live_design_review_gate", "complete": complete},
    )


def persist_inv_suite_attestation(log: FactLog, *, green: bool, at: str) -> None:
    log.append(
        event_id=f"live-inv-suite-{at[:10]}",
        event_type="deployment",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id="live-readiness-phase25",
        writer_id=WRITER_ID,
        payload={"kind": "live_inv_suite_attestation", "green": green},
    )


def persist_matrix_attestation(log: FactLog, *, green: bool, at: str) -> None:
    log.append(
        event_id=f"live-matrix-{at[:10]}",
        event_type="deployment",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id="live-readiness-phase25",
        writer_id=WRITER_ID,
        payload={"kind": "live_verification_matrix_attestation", "green": green},
    )


def persist_sim_adequacy_attestation(log: FactLog, *, gate_met: bool, at: str) -> None:
    log.append(
        event_id=f"live-sim-adequacy-{at[:10]}",
        event_type="deployment",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id="live-readiness-phase25",
        writer_id=WRITER_ID,
        payload={"kind": "live_sim_adequacy_attestation", "gate_met": gate_met},
    )


def persist_written_broker_verification(log: FactLog, *, on_file: bool, at: str) -> None:
    log.append(
        event_id=f"live-written-broker-{at[:10]}",
        event_type="owner_action",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id="live-readiness-phase25",
        writer_id=WRITER_ID,
        payload={"kind": "live_written_broker_verification", "on_file": on_file},
    )


def persist_cg_live_confirmation(log: FactLog, *, initial_advisory_zero: bool, at: str) -> None:
    log.append(
        event_id=f"live-cg-live-{at[:10]}",
        event_type="deployment",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id="live-readiness-phase25",
        writer_id=WRITER_ID,
        payload={"kind": "live_cg_live_confirmation", "initial_advisory_zero": initial_advisory_zero},
    )


def persist_rpo_rto_attestation(
    log: FactLog,
    *,
    rpo_minutes: int,
    rto_minutes: int,
    at: str,
) -> None:
    log.append(
        event_id=f"live-rpo-rto-{at[:10]}",
        event_type="deployment",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id="live-readiness-phase25",
        writer_id=WRITER_ID,
        payload={
            "kind": "live_rpo_rto_attestation",
            "owner_set": True,
            "rpo_minutes": rpo_minutes,
            "rto_minutes": rto_minutes,
        },
    )
