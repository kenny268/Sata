"""One-click adequacy report (**A-P1-01**)."""

from __future__ import annotations

import hashlib
import json

from sate_adequacy.champion import ChampionVerdict
from sate_adequacy.criteria import CriterionResult, evaluate_all
from sate_adequacy.evidence import SimAdequacyEvidence
from sate_adequacy.export_dashboard import performance_dashboard_export


def build_adequacy_report(
    evidence: SimAdequacyEvidence,
    *,
    champion: ChampionVerdict | None = None,
) -> dict[str, object]:
    criteria = evaluate_all(evidence)
    payload: dict[str, object] = {
        "generated_at": evidence.generated_at,
        "strategy_version_frozen": evidence.strategy_version_frozen,
        "criteria": [_criterion_dict(item) for item in criteria],
        "software_ready": _software_ready(criteria),
        "overall_pass": _overall_pass(criteria),
        "blockers": ["A-DEC-03"] if any(c.criterion_id == "A-SIM-04" and c.status == "blocked" for c in criteria) else [],
        "performance_dashboard": performance_dashboard_export(evidence),
    }
    if champion is not None:
        payload["champion_challenger"] = {
            "champion": champion.champion,
            "challenger": champion.challenger,
            "winner": champion.winner,
            "promotion_params_frozen": champion.promotion_params_frozen,
            "detail": champion.detail,
        }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    payload["report_digest"] = digest
    return payload


def _criterion_dict(item: CriterionResult) -> dict[str, str]:
    return {"id": item.criterion_id, "status": item.status, "detail": item.detail}


def _software_ready(criteria: list[CriterionResult]) -> bool:
    return all(item.status in {"pass", "blocked", "pending"} for item in criteria)


def _overall_pass(criteria: list[CriterionResult]) -> bool:
    return all(item.status == "pass" for item in criteria)
