"""Fact-log persistence for verification evidence."""

from __future__ import annotations

from sate_factlog.log import FactLog

from sate_compliance.bat_protective import ProtectiveOrderBat
from sate_compliance.blockers import BlockerRecord
from sate_compliance.evidence import BrokerEvidencePackage
from sate_compliance.sign_off import OwnerSignOff
from sate_compliance.tax_memo import TaxReportingMemo

WRITER_ID = "compliance-a"


def persist_evidence_package(log: FactLog, package: BrokerEvidencePackage, *, at: str) -> None:
    log.append(
        event_id=f"broker-evidence-{package.package_id}",
        event_type="deployment",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id="broker-verification",
        writer_id=WRITER_ID,
        payload={"kind": "broker_evidence_package", **package.to_dict()},
    )


def persist_sign_off(log: FactLog, sign_off: OwnerSignOff, *, at: str) -> None:
    log.append(
        event_id=f"broker-signoff-{sign_off.sign_off_id}",
        event_type="owner_action",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id="broker-verification",
        writer_id=WRITER_ID,
        payload={
            "kind": "broker_owner_sign_off",
            "sign_off_id": sign_off.sign_off_id,
            "owner": sign_off.owner,
            "signed_at": sign_off.signed_at,
            "evidence_package_id": sign_off.evidence_package_id,
            "attestation": sign_off.attestation,
        },
    )


def persist_tax_memo(log: FactLog, memo: TaxReportingMemo, *, at: str) -> None:
    log.append(
        event_id=f"broker-tax-{memo.memo_id}",
        event_type="deployment",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id="broker-verification",
        writer_id=WRITER_ID,
        payload={
            "kind": "broker_tax_memo",
            "memo_id": memo.memo_id,
            "jurisdiction": memo.jurisdiction,
            "reporting_currency_rule": memo.reporting_currency_rule,
            "professional_review_required": memo.professional_review_required,
        },
    )


def persist_blockers(log: FactLog, blockers: tuple[BlockerRecord, ...], *, at: str) -> None:
    log.append(
        event_id=f"broker-blockers-{at[:10]}",
        event_type="deployment",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id="broker-verification",
        writer_id=WRITER_ID,
        payload={
            "kind": "broker_blockers",
            "records": [
                {
                    "decision_id": item.decision_id,
                    "status": item.status,
                    "note": item.note,
                }
                for item in blockers
            ],
        },
    )


def persist_bat_verification(log: FactLog, bat: ProtectiveOrderBat, *, at: str) -> None:
    log.append(
        event_id=f"bat-protective-{at[:10]}",
        event_type="deployment",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id="broker-verification",
        writer_id=WRITER_ID,
        payload={
            "kind": "bat_protective_verification",
            "gate_met": bat.gate_met(),
            "steps": list(bat.steps),
        },
    )
