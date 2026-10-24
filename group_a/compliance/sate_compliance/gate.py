"""LIVE readiness gate (**INV-08**, **A-P0-20**)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sate_compliance.blockers import BlockerRecord, blockers_allow_live_arm, open_blocker_ids
from sate_compliance.evidence import BrokerEvidencePackage
from sate_compliance.relay_policy import RelayPolicy
from sate_compliance.sign_off import OwnerSignOff
from sate_compliance.tax_memo import TaxReportingMemo


@dataclass(frozen=True)
class BrokerLiveGate:
    package: BrokerEvidencePackage | None
    blockers: tuple[BlockerRecord, ...]
    sign_off: OwnerSignOff | None
    tax_memo: TaxReportingMemo | None
    relay: RelayPolicy
    bat_protective_ok: bool

    def block_reasons(self) -> list[str]:
        return assess_live_readiness(
            package=self.package,
            blockers=self.blockers,
            sign_off=self.sign_off,
            tax_memo=self.tax_memo,
            relay=self.relay,
            bat_protective_ok=self.bat_protective_ok,
        )


def assess_live_readiness(
    *,
    package: BrokerEvidencePackage | None,
    blockers: tuple[BlockerRecord, ...],
    sign_off: OwnerSignOff | None,
    tax_memo: TaxReportingMemo | None,
    relay: RelayPolicy,
    bat_protective_ok: bool,
) -> list[str]:
    reasons: list[str] = []
    if package is None:
        reasons.append("broker_evidence_missing")
        return reasons
    if not package.known_rules_complete:
        reasons.append("inv08_unknown_rules_disabled")
    if not package.protective_orders_verified or not bat_protective_ok:
        reasons.append("bat_protective_orders_unverified")
    if tax_memo is not None and not tax_memo.slot_filled():
        reasons.append("a_fee_05_tax_memo_incomplete")
    if not relay.sec_ok():
        reasons.append("a_dec_08_relay_policy_invalid")
    reasons.extend(f"decision_open:{item}" for item in open_blocker_ids(blockers))
    if not blockers_allow_live_arm(blockers) and any(
        item.decision_id == "A-DEC-10" and item.status == "BLOCKED" for item in blockers
    ):
        reasons.append("a_dec_10_blocked_live_impossible")
    if sign_off is None or not sign_off.present:
        reasons.append("owner_sign_off_missing")
    elif sign_off.evidence_package_id != package.package_id:
        reasons.append("sign_off_package_mismatch")
    return reasons


@dataclass
class GateAssessment:
    reasons: list[str] = field(default_factory=list)

    @property
    def live_arm_allowed(self) -> bool:
        return not self.reasons
