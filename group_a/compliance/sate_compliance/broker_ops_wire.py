"""Wire LIVE arm preflight to stored verification evidence."""

from __future__ import annotations

import os

from sate_factlog.log import FactLog

from sate_compliance.bat_protective import ProtectiveOrderBat
from sate_compliance.fact_load import blockers_or_default, load_broker_state
from sate_compliance.gate import BrokerLiveGate
from sate_compliance.persist import (
    persist_bat_verification,
    persist_blockers,
    persist_evidence_package,
    persist_sign_off,
    persist_tax_memo,
)
from sate_compliance.relay_policy import relay_policy_from_env
from sate_compliance.staging import complete_gate, incomplete_gate
from sate_compliance.tax_memo import TaxReportingMemo


def gate_for_arm(log: FactLog | None, *, as_of: str) -> BrokerLiveGate:
    relay = relay_policy_from_env()
    if log is None:
        return incomplete_gate()
    state = load_broker_state(log, as_of=as_of)
    bat_ok = state.bat_protective_ok or bat_ok_from_env()
    if (
        state.package is None
        and state.sign_off is None
        and state.tax_memo is None
        and state.blockers is None
        and not state.bat_protective_ok
    ):
        return incomplete_gate()
    return BrokerLiveGate(
        package=state.package,
        blockers=blockers_or_default(state.blockers),
        sign_off=state.sign_off,
        tax_memo=state.tax_memo
        or TaxReportingMemo(
            memo_id="",
            jurisdiction="KE",
            reporting_currency_rule="",
            professional_review_required=True,
        ),
        relay=relay,
        bat_protective_ok=bat_ok,
    )


def bat_ok_from_env() -> bool:
    return os.environ.get("SATE_BAT_PROTECTIVE_VERIFIED", "").lower() in {"1", "true", "yes"}


def written_verification_on_file() -> bool:
    return os.environ.get("SATE_BROKER_WRITTEN_VERIFICATION", "").lower() in {"1", "true", "yes"}


def seed_staging_verification(log: FactLog, *, at: str) -> BrokerLiveGate:
    gate = complete_gate()
    assert gate.package is not None
    assert gate.sign_off is not None
    assert gate.tax_memo is not None
    persist_evidence_package(log, gate.package, at=at)
    persist_sign_off(log, gate.sign_off, at=at)
    persist_tax_memo(log, gate.tax_memo, at=at)
    persist_blockers(log, gate.blockers, at=at)
    bat = ProtectiveOrderBat()
    bat.record_demo_verification()
    persist_bat_verification(log, bat, at=at)
    return gate


def persist_mt5_bat_result(log: FactLog, bat: ProtectiveOrderBat, *, at: str) -> None:
    persist_bat_verification(log, bat, at=at)
