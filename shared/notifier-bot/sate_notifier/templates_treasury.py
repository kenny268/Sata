"""Treasury notification templates (**TG-PO-14**)."""

from __future__ import annotations

_COMBINED_LABEL = "Combined reporting — not transferable and not used for sizing or eligibility"


def treasury_card(
    *,
    scope: str,
    cash_floor: str,
    obligations: str,
    reimbursement_state: str,
) -> dict[str, str]:
    tag = f"[{scope}-LIVE]" if scope != "ALL" else "[ALL]"
    return {
        "text": (
            f"{tag} TREASURY NOTICE\n"
            f"Cash floor: {cash_floor}\n"
            f"Open obligations: {obligations}\n"
            f"Reimbursement: {reimbursement_state}\n"
            f"{_COMBINED_LABEL if scope == 'ALL' else ''}"
        ).strip(),
        "category": "TREASURY",
        "severity": "NOTICE",
    }
