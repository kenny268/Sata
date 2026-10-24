"""Load broker verification artifacts from the fact log."""

from __future__ import annotations

import os
from dataclasses import dataclass

from sate_factlog.errors import Unauthorized
from sate_factlog.log import FactLog

from sate_compliance.blockers import BlockerRecord, default_blockers
from sate_compliance.evidence import BrokerEvidencePackage
from sate_compliance.sign_off import OwnerSignOff
from sate_compliance.tax_memo import TaxReportingMemo

READER_ID = "compliance-a"


@dataclass(frozen=True)
class LoadedBrokerState:
    package: BrokerEvidencePackage | None
    sign_off: OwnerSignOff | None
    tax_memo: TaxReportingMemo | None
    blockers: tuple[BlockerRecord, ...] | None
    bat_protective_ok: bool


def load_broker_state(
    log: FactLog,
    *,
    as_of: str,
    reader_id: str | None = None,
) -> LoadedBrokerState:
    rows = _replay(log, as_of=as_of, reader_id=reader_id)
    package: BrokerEvidencePackage | None = None
    sign_off: OwnerSignOff | None = None
    tax_memo: TaxReportingMemo | None = None
    blockers: tuple[BlockerRecord, ...] | None = None
    bat_ok = False
    for row in rows:
        kind = row.payload.get("kind")
        if kind == "broker_evidence_package":
            package = BrokerEvidencePackage.from_dict(_payload_without_kind(row.payload))
        elif kind == "broker_owner_sign_off":
            sign_off = OwnerSignOff(
                sign_off_id=str(row.payload["sign_off_id"]),
                owner=str(row.payload["owner"]),
                signed_at=str(row.payload["signed_at"]),
                evidence_package_id=str(row.payload["evidence_package_id"]),
                attestation=str(row.payload.get("attestation", "")),
            )
        elif kind == "broker_tax_memo":
            tax_memo = TaxReportingMemo(
                memo_id=str(row.payload["memo_id"]),
                jurisdiction=str(row.payload["jurisdiction"]),
                reporting_currency_rule=str(row.payload["reporting_currency_rule"]),
                professional_review_required=bool(row.payload.get("professional_review_required", True)),
            )
        elif kind == "broker_blockers":
            blockers = tuple(
                BlockerRecord(
                    decision_id=str(item["decision_id"]),
                    status=item["status"],  # type: ignore[arg-type]
                    note=str(item.get("note", "")),
                )
                for item in row.payload.get("records", [])
            )
        elif kind == "bat_protective_verification" and row.payload.get("gate_met"):
            bat_ok = True
    return LoadedBrokerState(
        package=package,
        sign_off=sign_off,
        tax_memo=tax_memo,
        blockers=blockers,
        bat_protective_ok=bat_ok,
    )


def _payload_without_kind(payload: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in payload.items() if key != "kind"}


def blockers_or_default(blockers: tuple[BlockerRecord, ...] | None) -> tuple[BlockerRecord, ...]:
    return blockers if blockers is not None else default_blockers()


def _replay(log: FactLog, *, as_of: str, reader_id: str | None) -> list:
    preferred = reader_id or os.environ.get("SATE_COMPLIANCE_READER", READER_ID)
    candidates: list[str] = []
    for item in (preferred, READER_ID, "control-api"):
        if item not in candidates:
            candidates.append(item)
    last: Exception | None = None
    for candidate in candidates:
        try:
            return log.replay_through(group_scope="A", as_of=as_of, reader_id=candidate)
        except Unauthorized as exc:
            last = exc
    if last is not None:
        raise last
    return []
