"""§7.4 evidence package store (**A-P0-20**)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import jsonschema

_SCHEMA = json.loads(
    (
        Path(__file__).resolve().parents[3]
        / "shared"
        / "schemas"
        / "broker-evidence-package.schema.json"
    ).read_text(encoding="utf-8")
)


@dataclass(frozen=True)
class BrokerEvidencePackage:
    package_id: str
    broker_id: str
    jurisdiction: str
    account_type: str
    products: tuple[str, ...]
    max_leverage: str
    withdrawal_mechanism: str
    protective_orders_verified: bool
    verification_date: str
    known_rules_complete: bool
    tax_memo_ref: str = ""
    appendix_d_ref: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "package_id": self.package_id,
            "broker_id": self.broker_id,
            "jurisdiction": self.jurisdiction,
            "account_type": self.account_type,
            "products": list(self.products),
            "max_leverage": self.max_leverage,
            "withdrawal_mechanism": self.withdrawal_mechanism,
            "protective_orders_verified": self.protective_orders_verified,
            "verification_date": self.verification_date,
            "known_rules_complete": self.known_rules_complete,
            "tax_memo_ref": self.tax_memo_ref,
            "appendix_d_ref": self.appendix_d_ref,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> BrokerEvidencePackage:
        validate_package(raw)
        return cls(
            package_id=str(raw["package_id"]),
            broker_id=str(raw["broker_id"]),
            jurisdiction=str(raw["jurisdiction"]),
            account_type=str(raw["account_type"]),
            products=tuple(str(item) for item in raw["products"]),  # type: ignore[arg-type]
            max_leverage=str(raw["max_leverage"]),
            withdrawal_mechanism=str(raw["withdrawal_mechanism"]),
            protective_orders_verified=bool(raw["protective_orders_verified"]),
            verification_date=str(raw["verification_date"]),
            known_rules_complete=bool(raw["known_rules_complete"]),
            tax_memo_ref=str(raw.get("tax_memo_ref", "")),
            appendix_d_ref=str(raw.get("appendix_d_ref", "")),
        )


def validate_package(raw: dict[str, object]) -> None:
    jsonschema.validate(raw, _SCHEMA)


def load_package(path: Path) -> BrokerEvidencePackage:
    return BrokerEvidencePackage.from_dict(json.loads(path.read_text(encoding="utf-8")))
