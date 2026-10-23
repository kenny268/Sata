"""Treasury notification templates (**TG-PO-14**)."""

from __future__ import annotations

from sate_notifier.tags import COMBINED_LABEL, scope_tag


def treasury_card(
    *,
    scope: str,
    cash_floor: str,
    obligations: str,
    reimbursement_state: str,
    mode: str = "",
) -> dict[str, str]:
    tag = scope_tag(scope, mode)
    combined = f"\n{COMBINED_LABEL}" if scope == "ALL" else ""
    return {
        "text": (
            f"{tag} TREASURY NOTICE\n"
            f"Cash floor: {cash_floor}\n"
            f"Open obligations: {obligations}\n"
            f"Reimbursement: {reimbursement_state}"
            f"{combined}"
        ),
        "category": "TREASURY",
        "severity": "NOTICE",
    }
