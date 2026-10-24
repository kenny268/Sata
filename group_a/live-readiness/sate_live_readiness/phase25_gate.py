"""Phase 25 LIVE readiness report."""

from __future__ import annotations

from sate_factlog.log import FactLog

from sate_live_readiness.decisions import load_cg_live_record
from sate_live_readiness.preflight_engine import LivePreflightInputs, assess_live_readiness
from sate_live_readiness.staging import complete_inputs, incomplete_inputs
from sate_live_readiness.verification_matrix import load_matrix, matrix_evidence_present


def build_phase25_report(
    log: FactLog | None,
    *,
    as_of: str,
    inputs: LivePreflightInputs | None = None,
) -> dict[str, object]:
    assessment_inputs = inputs or incomplete_inputs(as_of=as_of)
    if inputs is None and log is not None:
        assessment_inputs = LivePreflightInputs(as_of=as_of, log=log)
    assessment = assess_live_readiness(assessment_inputs)
    matrix = load_matrix()
    return {
        "phase": 25,
        "as_of": as_of,
        "a_p1_06_preflight_ok": not assessment.block_reasons(),
        "block_reasons": assessment.block_reasons(),
        "verification_matrix": {
            "classes": list(matrix.get("classes", {}).keys()),
            "evidence_present": matrix_evidence_present(),
        },
        "cg_live": load_cg_live_record(),
        "phase25_exit_met": not assessment.block_reasons(),
    }


def staging_complete_report(*, as_of: str = "2026-10-23T21:00:00Z") -> dict[str, object]:
    return build_phase25_report(None, as_of=as_of, inputs=complete_inputs(as_of=as_of))
