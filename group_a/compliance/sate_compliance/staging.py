"""Staging fixtures for SIM and tests."""

from __future__ import annotations

from sate_compliance.blockers import BlockerRecord, default_blockers
from sate_compliance.evidence import BrokerEvidencePackage
from sate_compliance.gate import BrokerLiveGate
from sate_compliance.relay_policy import RelayPolicy
from sate_compliance.sign_off import OwnerSignOff
from sate_compliance.tax_memo import TaxReportingMemo


def incomplete_gate() -> BrokerLiveGate:
    package = BrokerEvidencePackage(
        package_id="exness-ke-stub",
        broker_id="exness",
        jurisdiction="KE",
        account_type="unverified",
        products=("forex",),
        max_leverage="unknown",
        withdrawal_mechanism="manual_portal",
        protective_orders_verified=False,
        verification_date="2026-01-01",
        known_rules_complete=False,
    )
    return BrokerLiveGate(
        package=package,
        blockers=default_blockers(),
        sign_off=None,
        tax_memo=TaxReportingMemo(
            memo_id="",
            jurisdiction="KE",
            reporting_currency_rule="",
            professional_review_required=True,
        ),
        relay=RelayPolicy(enabled=False),
        bat_protective_ok=False,
    )


def complete_gate() -> BrokerLiveGate:
    package = BrokerEvidencePackage(
        package_id="exness-ke-verified",
        broker_id="exness",
        jurisdiction="KE",
        account_type="standard",
        products=("forex", "cfd"),
        max_leverage="1:200",
        withdrawal_mechanism="manual_portal",
        protective_orders_verified=True,
        verification_date="2026-10-01",
        known_rules_complete=True,
        tax_memo_ref="tax-memo-ke-2026",
        appendix_d_ref="APP-D-BROKER-01",
    )
    blockers = (
        BlockerRecord("A-DEC-01", "RESOLVED", "min lot policy documented"),
        BlockerRecord("A-DEC-08", "BLOCKED", "relay not enabled"),
        BlockerRecord("A-DEC-10", "RESOLVED", "written verification on file"),
    )
    sign_off = OwnerSignOff(
        sign_off_id="so-1",
        owner="owner",
        signed_at="2026-10-20T00:00:00Z",
        evidence_package_id=package.package_id,
        attestation="broker rules verified for Kenya Exness SIM-to-LIVE path",
    )
    return BrokerLiveGate(
        package=package,
        blockers=blockers,
        sign_off=sign_off,
        tax_memo=TaxReportingMemo(
            memo_id="tax-memo-ke-2026",
            jurisdiction="KE",
            reporting_currency_rule="USD broker balance; KES reporting per professional memo",
            professional_review_required=True,
        ),
        relay=RelayPolicy(enabled=False),
        bat_protective_ok=True,
    )
