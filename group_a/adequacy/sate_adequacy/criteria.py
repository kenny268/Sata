"""Evaluate **A-SIM-01–08** with explicit blocked states."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sate_adequacy.evidence import SimAdequacyEvidence

Status = Literal["pass", "fail", "blocked", "pending"]

A_DEC_03_OPEN = True


@dataclass(frozen=True)
class CriterionResult:
    criterion_id: str
    status: Status
    detail: str


def evaluate_all(evidence: SimAdequacyEvidence) -> list[CriterionResult]:
    results: list[CriterionResult] = []
    results.append(_sim01(evidence))
    results.append(_sim02(evidence))
    results.append(_sim03(evidence))
    results.append(_sim04(evidence))
    results.append(_sim05(evidence))
    results.append(_sim06(evidence))
    results.append(_sim07(evidence))
    results.append(_sim08(evidence))
    return results


def _sim01(evidence: SimAdequacyEvidence) -> CriterionResult:
    ok = evidence.sim_months_continuous >= 6.0
    return CriterionResult(
        "A-SIM-01",
        "pass" if ok else "pending",
        f"{evidence.sim_months_continuous:.2f} months continuous SIM (need 6)",
    )


def _sim02(evidence: SimAdequacyEvidence) -> CriterionResult:
    ok = evidence.reconciliation_clean_rate >= 0.95
    return CriterionResult(
        "A-SIM-02",
        "pass" if ok else "fail",
        f"clean reconciliation {evidence.reconciliation_clean_rate:.1%} (need 95%)",
    )


def _sim03(evidence: SimAdequacyEvidence) -> CriterionResult:
    ok = evidence.net_sharpe_after_costs >= 1.2
    return CriterionResult(
        "A-SIM-03",
        "pass" if ok else "fail",
        f"net Sharpe {evidence.net_sharpe_after_costs:.2f} (need 1.2)",
    )


def _sim04(evidence: SimAdequacyEvidence) -> CriterionResult:
    if A_DEC_03_OPEN:
        return CriterionResult(
            "A-SIM-04",
            "blocked",
            "return hurdle blocked on open A-DEC-03 (6% vs cost-derived)",
        )
    months = evidence.monthly_returns_net[-3:]
    if len(months) < 3:
        return CriterionResult("A-SIM-04", "pending", "need 3 rolling month-end returns")
    ok = all(value >= 0.06 for value in months)
    return CriterionResult(
        "A-SIM-04",
        "pass" if ok else "fail",
        f"last 3 net monthly returns {months}",
    )


def _sim05(evidence: SimAdequacyEvidence) -> CriterionResult:
    trades_ok = evidence.trade_count >= 200
    bootstrap_ok = (
        evidence.bootstrap_excess_lower_bound is not None
        and evidence.bootstrap_excess_lower_bound > 0.0
    )
    ok = trades_ok or bootstrap_ok
    return CriterionResult(
        "A-SIM-05",
        "pass" if ok else "fail",
        f"trades={evidence.trade_count}, bootstrap_lb={evidence.bootstrap_excess_lower_bound}",
    )


def _sim06(evidence: SimAdequacyEvidence) -> CriterionResult:
    ok = evidence.l2_plus_unresolved_last_60d == 0
    return CriterionResult(
        "A-SIM-06",
        "pass" if ok else "fail",
        f"unresolved L2+ in 60d={evidence.l2_plus_unresolved_last_60d}",
    )


def _sim07(evidence: SimAdequacyEvidence) -> CriterionResult:
    ok = evidence.parameter_changes_last_3_months == 0
    return CriterionResult(
        "A-SIM-07",
        "pass" if ok else "fail",
        f"parameter changes in 3mo={evidence.parameter_changes_last_3_months}",
    )


def _sim08(evidence: SimAdequacyEvidence) -> CriterionResult:
    ok = evidence.untradeable_session_rate < 0.5
    return CriterionResult(
        "A-SIM-08",
        "pass" if ok else "fail",
        f"untradeable session rate {evidence.untradeable_session_rate:.1%}",
    )
