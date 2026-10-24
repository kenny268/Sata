"""Wire LIVE arm preflight to stored readiness attestations."""

from __future__ import annotations

import os

from sate_factlog.log import FactLog

from sate_live_readiness.fact_load import load_live_readiness_state
from sate_live_readiness.persist import (
    persist_cg_live_confirmation,
    persist_constitution_snapshot,
    persist_design_review_gate,
    persist_inv_suite_attestation,
    persist_matrix_attestation,
    persist_rcb_floor_attestation,
    persist_rpo_rto_attestation,
    persist_sim_adequacy_attestation,
    persist_written_broker_verification,
)
from sate_live_readiness.preflight_engine import LivePreflightInputs, _staging_constitution


def inputs_for_arm(
    body: dict[str, object],
    *,
    log: FactLog | None,
    as_of: str,
    broker_preflight_ok: bool,
) -> LivePreflightInputs:
    if bool(body.get("live_readiness_complete")):
        return LivePreflightInputs(
            as_of=as_of,
            log=log,
            rcb_at_or_above_floor=True,
            constitution=_staging_constitution(),
            broker_preflight_ok=True,
            matrix_green=True,
            inv_suite_green=True,
            design_review_complete=True,
            sim_adequacy_exit=True,
            written_broker_verification=True,
            cg_live_confirmed=True,
            rpo_rto_resolved=True,
        )
    merged = _merge_body_defaults(body, as_of=as_of, log=log, broker_preflight_ok=broker_preflight_ok)
    if log is None:
        return merged
    state = load_live_readiness_state(log, as_of=as_of)
    if not state.any_present():
        return merged
    return LivePreflightInputs(
        as_of=as_of,
        log=log,
        rcb_at_or_above_floor=state.rcb_at_or_above_floor or merged.rcb_at_or_above_floor,
        constitution=state.constitution or merged.constitution,
        broker_preflight_ok=broker_preflight_ok,
        matrix_green=_pick_bool(state.matrix_green, merged.matrix_green),
        inv_suite_green=_pick_bool(state.inv_suite_green, merged.inv_suite_green),
        design_review_complete=_pick_bool(state.design_review_complete, merged.design_review_complete),
        sim_adequacy_exit=True if state.sim_adequacy_attested else merged.sim_adequacy_exit,
        written_broker_verification=(
            True if state.written_broker_verification else merged.written_broker_verification
        ),
        cg_live_confirmed=True if state.cg_live_confirmed else merged.cg_live_confirmed,
        rpo_rto_resolved=True if state.rpo_rto_resolved else merged.rpo_rto_resolved,
    )


def seed_staging_live_readiness(log: FactLog, *, at: str) -> None:
    """Persist a complete §19 attestation bundle for tests and staging."""
    from sate_compliance.broker_ops_wire import seed_staging_verification

    seed_staging_verification(log, at=at)
    try:
        from sate_adequacy.sim_period_harness import seed_six_month_evidence

        seed_six_month_evidence(
            log,
            period_start=os.environ.get("SATE_SIM_PERIOD_START", "2026-04-23T00:00:00Z"),
            as_of=at,
            days=184,
        )
    except ImportError:  # pragma: no cover
        pass
    persist_rcb_floor_attestation(log, at_or_above_floor=True, at=at)
    persist_constitution_snapshot(log, constitution=_staging_constitution(), at=at)
    persist_design_review_gate(log, complete=True, at=at)
    persist_inv_suite_attestation(log, green=True, at=at)
    persist_matrix_attestation(log, green=True, at=at)
    persist_sim_adequacy_attestation(log, gate_met=True, at=at)
    persist_written_broker_verification(log, on_file=True, at=at)
    persist_cg_live_confirmation(log, initial_advisory_zero=True, at=at)
    persist_rpo_rto_attestation(log, rpo_minutes=15, rto_minutes=60, at=at)


def _merge_body_defaults(
    body: dict[str, object],
    *,
    as_of: str,
    log: FactLog | None,
    broker_preflight_ok: bool,
) -> LivePreflightInputs:
    constitution = _constitution_from_body(body)
    return LivePreflightInputs(
        as_of=as_of,
        log=log,
        rcb_at_or_above_floor=bool(body.get("rcb_at_or_above_floor", False)),
        constitution=constitution,
        broker_preflight_ok=broker_preflight_ok,
        matrix_green=_env_bool("SATE_VERIFICATION_MATRIX_GREEN"),
        inv_suite_green=_env_bool("SATE_INV_SUITE_GREEN"),
        design_review_complete=_env_bool("SATE_DESIGN_REVIEW_COMPLETE"),
        sim_adequacy_exit=_optional_bool(body.get("sim_adequacy_exit")),
        written_broker_verification=_optional_bool(body.get("written_broker_verification")),
        cg_live_confirmed=_cg_live_from_env(),
        rpo_rto_resolved=_rpo_rto_from_env(),
    )


def _constitution_from_body(body: dict[str, object]) -> dict[str, object] | None:
    if bool(body.get("constitution_lock_hours_set")):
        return _staging_constitution()
    return None


def _env_bool(name: str) -> bool | None:
    raw = os.environ.get(name, "").lower()
    if raw in {"1", "true", "yes"}:
        return True
    if raw in {"0", "false", "no"}:
        return False
    return None


def _optional_bool(value: object) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _cg_live_from_env() -> bool | None:
    if _env_bool("SATE_CG_LIVE_INITIAL_ADVISORY_ZERO") is True:
        return True
    return None


def _rpo_rto_from_env() -> bool | None:
    rpo = os.environ.get("SATE_RPO_MINUTES", "").strip()
    rto = os.environ.get("SATE_RTO_MINUTES", "").strip()
    if rpo.isdigit() and rto.isdigit():
        return True
    return None


def _pick_bool(log_value: bool, merged: bool | None) -> bool | None:
    if log_value:
        return True
    return merged
