"""Staging inputs for tests and compose smoke."""

from __future__ import annotations

from sate_live_readiness.preflight_engine import (
    LivePreflightInputs,
    LiveReadinessAssessment,
    _staging_constitution,
    assess_live_readiness,
)


def incomplete_inputs(*, as_of: str = "2026-10-23T21:00:00Z") -> LivePreflightInputs:
    return LivePreflightInputs(as_of=as_of)


def complete_inputs(*, as_of: str = "2026-10-23T21:00:00Z") -> LivePreflightInputs:
    return LivePreflightInputs(
        as_of=as_of,
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


def incomplete_assessment() -> LiveReadinessAssessment:
    return assess_live_readiness(incomplete_inputs())


def complete_assessment() -> LiveReadinessAssessment:
    return assess_live_readiness(complete_inputs())
