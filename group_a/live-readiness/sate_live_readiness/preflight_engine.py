"""**A-P1-06** LIVE preflight engine (**§19**, **AM-03**)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from sate_factlog.log import FactLog

from sate_live_readiness.cg_live import cg_live_reasons
from sate_live_readiness.decisions import a_dec_04_reasons, a_dec_09_reasons
from sate_live_readiness.design_review import design_review_reasons
from sate_live_readiness.invariants import inv_suite_block_reasons
from sate_live_readiness.section19 import Section19Input, section19_reasons
from sate_live_readiness.verification_matrix import matrix_green

try:
    from sate_adequacy.phase23_gate import build_phase23_report, resolve_period
except ImportError:  # pragma: no cover
    build_phase23_report = None  # type: ignore[misc, assignment]
    resolve_period = None  # type: ignore[misc, assignment

try:
    from sate_compliance.broker_ops_wire import written_verification_on_file
except ImportError:  # pragma: no cover
    written_verification_on_file = lambda: False  # type: ignore[misc, assignment]


@dataclass(frozen=True)
class LiveReadinessAssessment:
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def block_reasons(self) -> list[str]:
        return list(self.reasons)


@dataclass(frozen=True)
class LivePreflightInputs:
    as_of: str
    log: FactLog | None = None
    rcb_at_or_above_floor: bool = False
    constitution: dict[str, object] | None = None
    broker_preflight_ok: bool = False
    matrix_green: bool | None = None
    inv_suite_green: bool | None = None
    design_review_complete: bool | None = None
    sim_adequacy_exit: bool | None = None
    written_broker_verification: bool | None = None
    cg_live_confirmed: bool | None = None
    rpo_rto_resolved: bool | None = None


def assess_live_readiness(inputs: LivePreflightInputs) -> LiveReadinessAssessment:
    reasons: list[str] = []
    if not inputs.rcb_at_or_above_floor:
        reasons.append("capital_rcb_below_reference_floor")

    reasons.extend(a_dec_04_reasons(inputs.constitution))
    if inputs.rpo_rto_resolved is not True:
        reasons.extend(a_dec_09_reasons())
    reasons.extend(cg_live_reasons(confirmed=inputs.cg_live_confirmed))
    reasons.extend(design_review_reasons(env_override=inputs.design_review_complete))
    reasons.extend(inv_suite_block_reasons(env_override=inputs.inv_suite_green))

    matrix_ok = matrix_green(env_override=inputs.matrix_green)
    if not matrix_ok:
        reasons.append("verification_matrix_incomplete")

    sim_ok = inputs.sim_adequacy_exit
    if sim_ok is None and inputs.log is not None and build_phase23_report is not None:
        sim_ok = _phase23_exit(inputs.log, as_of=inputs.as_of)
    if not sim_ok:
        reasons.append("sim_adequacy_exit_not_met")

    written = inputs.written_broker_verification
    if written is None:
        written = written_verification_on_file()
    if not written:
        reasons.append("broker_written_verification_missing")

    inv_ok = inputs.inv_suite_green is True or (
        inputs.inv_suite_green is None and matrix_ok and not inv_suite_block_reasons()
    )
    section19 = Section19Input(
        architecture_ok=inv_ok,
        code_ok=matrix_ok,
        security_ok=matrix_ok,
        testing_ok=matrix_ok,
        broker_ok=inputs.broker_preflight_ok,
        operations_ok=bool(sim_ok),
    )
    reasons.extend(section19_reasons(section19))
    return LiveReadinessAssessment(reasons=tuple(dict.fromkeys(reasons)))


def build_inputs_from_arm_body(
    body: dict[str, object],
    *,
    log: FactLog | None,
    as_of: str,
    broker_preflight_ok: bool,
) -> LivePreflightInputs:
    from sate_live_readiness.live_ops_wire import inputs_for_arm

    return inputs_for_arm(
        body,
        log=log,
        as_of=as_of,
        broker_preflight_ok=broker_preflight_ok,
    )


def assess_for_arm(
    body: dict[str, object],
    *,
    log: FactLog | None,
    as_of: str,
    broker_preflight_ok: bool,
) -> LiveReadinessAssessment:
    inputs = build_inputs_from_arm_body(
        body,
        log=log,
        as_of=as_of,
        broker_preflight_ok=broker_preflight_ok,
    )
    return assess_live_readiness(inputs)


def _phase23_exit(log: FactLog, *, as_of: str) -> bool:
    if build_phase23_report is None or resolve_period is None:
        return False
    try:
        period = resolve_period(log, as_of=as_of, env_start=os.environ.get("SATE_SIM_PERIOD_START"))
        report = build_phase23_report(log, as_of=as_of, period=period)
        return bool(report.get("phase23_exit_met"))
    except (ValueError, PermissionError):
        return False


def _staging_constitution() -> dict[str, object]:
    return {
        "meta": {"tighten_lock_hours": 24, "loosen_lock_hours": 72},
        "risk": {"broker_balance_cap": "10000"},
        "mode": {"state": "SIM"},
    }


