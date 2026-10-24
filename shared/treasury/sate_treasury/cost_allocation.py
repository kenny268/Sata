"""Shared-cost allocation (**A-P1-04**, default **A-DEC-05** pro-rata RCB)."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

RULE_PRO_RATA_RCB = "pro_rata_rcb"
RULE_VERSION = "2026-10-23"


def pro_rata_rcb_shares(
    *,
    amount: str,
    rcb_a: str,
    rcb_b: str,
) -> dict[str, str]:
    total = Decimal(rcb_a) + Decimal(rcb_b)
    if total <= 0:
        raise ValueError("RCB total must be positive for allocation")
    gross = Decimal(amount)
    share_a = (gross * Decimal(rcb_a) / total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    share_b = gross - share_a
    return {"A": str(share_a), "B": str(share_b)}


def shared_cost_payload(
    *,
    cost_id: str,
    amount: str,
    currency: str,
    vendor: str,
    evidence: str,
    path: str,
    rcb_a: str,
    rcb_b: str,
    rule: str = RULE_PRO_RATA_RCB,
    reimbursement_ids: dict[str, str] | None = None,
) -> dict[str, object]:
    if rule != RULE_PRO_RATA_RCB:
        raise ValueError(f"unsupported allocation rule {rule!r}")
    shares = pro_rata_rcb_shares(amount=amount, rcb_a=rcb_a, rcb_b=rcb_b)
    ids = reimbursement_ids or {"A": f"reimb-{cost_id}-a", "B": f"reimb-{cost_id}-b"}
    share_rows = [
        {"scope": "A", "amount": shares["A"], "reimbursement_id": ids["A"]},
        {"scope": "B", "amount": shares["B"], "reimbursement_id": ids["B"]},
    ]
    return {
        "cost_id": cost_id,
        "path": path,
        "amount": amount,
        "currency": currency,
        "vendor": vendor,
        "evidence": evidence,
        "basis": f"{rule}:rcb_a={rcb_a},rcb_b={rcb_b}",
        "rule_version": RULE_VERSION,
        "shares": share_rows,
    }


def submit_pro_rata_shared_cost(
    log,
    state,
    *,
    cost_id: str,
    amount: str,
    currency: str,
    vendor: str,
    evidence: str,
    path: str,
    rcb_a: str,
    rcb_b: str,
    rule: str = RULE_PRO_RATA_RCB,
    reimbursement_ids: dict[str, str] | None = None,
    **identity: str,
):
    """Fact-log + ledger helper (**A-P1-04**)."""
    from sate_treasury.sourced import submit_shared_cost

    payload = shared_cost_payload(
        cost_id=cost_id,
        amount=amount,
        currency=currency,
        vendor=vendor,
        evidence=evidence,
        path=path,
        rcb_a=rcb_a,
        rcb_b=rcb_b,
        rule=rule,
        reimbursement_ids=reimbursement_ids,
    )
    return submit_shared_cost(log, state, payload, **identity)
