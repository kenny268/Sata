"""Reimbursement-owed projection. Owner-paid costs do not enter broker cash."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation

from sate_capital.ledger import CapitalState

from sate_treasury.errors import TreasuryError

TAGS = frozenset({"A", "B", "GLOBAL"})
SCOPES = frozenset({"A", "B"})
PATHS = frozenset({"owner_paid", "broker_deducted"})
STATUSES = (
    "COST_RECORDED",
    "REIMBURSEMENT_ELIGIBILITY_PENDING",
    "REIMBURSEMENT_AUTHORIZED",
    "WITHDRAWAL_PENDING_OWNER",
    "OWNER_CONFIRMED",
    "BROKER_RECONCILIATION",
    "REIMBURSED",
    "MISSED",
)
_NEXT = {
    "COST_RECORDED": frozenset({"REIMBURSEMENT_ELIGIBILITY_PENDING"}),
    "REIMBURSEMENT_ELIGIBILITY_PENDING": frozenset({"REIMBURSEMENT_AUTHORIZED"}),
    "REIMBURSEMENT_AUTHORIZED": frozenset({"WITHDRAWAL_PENDING_OWNER"}),
    "WITHDRAWAL_PENDING_OWNER": frozenset({"OWNER_CONFIRMED", "MISSED"}),
    "OWNER_CONFIRMED": frozenset({"BROKER_RECONCILIATION"}),
    "BROKER_RECONCILIATION": frozenset({"REIMBURSED", "MISSED"}),
    "REIMBURSED": frozenset(),
    "MISSED": frozenset(),
}
_ZERO = Decimal("0")
_CASH_FIELDS = frozenset({
    "cash",
    "withdrawable",
    "withdrawable_cash",
    "settled",
    "equity",
    "ratified_base",
    "combined_equity",
    "combined_rcb",
    "portfolio_total",
})


@dataclass(frozen=True)
class Cost:
    cost_id: str
    tag: str
    path: str
    amount: str
    currency: str
    vendor: str
    evidence: str


@dataclass(frozen=True)
class Allocation:
    cost_id: str
    basis: str
    rule_version: str
    evidence: str
    share_a: str
    share_b: str


@dataclass(frozen=True)
class Obligation:
    obligation_id: str
    group_scope: str
    owner: str
    due_date: str
    currency: str
    amount: str
    broker_dependency: str
    reserve: bool
    exposure_reduction_required: bool


@dataclass(frozen=True)
class Case:
    reimbursement_id: str
    cost_id: str
    group_scope: str
    amount: str
    currency: str
    status: str
    broker_matched: bool | None
    defer_reason: str

    @property
    def withdrawal_success(self) -> bool:
        return self.status == "REIMBURSED"


@dataclass(frozen=True)
class TreasuryState:
    costs: tuple[Cost, ...]
    cases: tuple[Case, ...]
    allocations: tuple[Allocation, ...]
    obligations: tuple[Obligation, ...]
    last_seq: int


def blank() -> TreasuryState:
    return TreasuryState(costs=(), cases=(), allocations=(), obligations=(), last_seq=0)


def owed(state: TreasuryState, scope: str) -> str:
    if scope not in SCOPES:
        raise TreasuryError(f"treasury owed refuses scope {scope!r}")
    total = _ZERO
    for case in state.cases:
        if case.group_scope == scope and case.status != "REIMBURSED":
            total += _dec(case.amount)
    return _text(total)


def dashboard(state: TreasuryState, scope: str) -> dict[str, object]:
    """Read-only reimbursement status for one group."""
    if scope not in SCOPES:
        raise TreasuryError(f"treasury view refuses scope {scope!r}")
    cases = []
    for case in state.cases:
        if case.group_scope != scope:
            continue
        cases.append(
            {
                "reimbursement_id": case.reimbursement_id,
                "status": case.status,
                "amount": case.amount,
                "currency": case.currency,
                "withdrawal_success": case.withdrawal_success,
                "notice_due": case.status == "REIMBURSEMENT_AUTHORIZED",
                "defer_reason": case.defer_reason,
            }
        )
    obligations = [
        item.obligation_id for item in state.obligations if item.group_scope == scope
    ]
    return {
        "group_scope": scope,
        "reimbursement_owed": owed(state, scope),
        "cases": cases,
        "obligations": obligations,
        "read_only": True,
    }


def project(records: list) -> TreasuryState:
    state = blank()
    for record in sorted(records, key=lambda item: item.seq):
        state = fold(state, record)
    return state


def fold(state: TreasuryState, record) -> TreasuryState:
    if record.seq <= state.last_seq:
        return state
    if record.event_type not in {"invoice", "reimbursement"}:
        return _advance(state, record.seq)
    if record.writer_id != "treasury":
        raise TreasuryError("treasury events must be written by the treasury service")
    return apply_event(state, record.payload, seq=record.seq)


def apply_event(state: TreasuryState, payload: dict[str, object], *, seq: int) -> TreasuryState:
    overlap = _CASH_FIELDS.intersection(payload)
    if overlap:
        names = ", ".join(sorted(overlap))
        raise TreasuryError(f"treasury event cannot carry broker cash: {names}")
    kind = str(payload.get("kind", ""))
    if kind == "cost":
        return _cost(state, payload, seq)
    if kind == "shared_cost":
        return _shared_cost(state, payload, seq)
    if kind == "obligation":
        return _obligation(state, payload, seq)
    if kind == "transition":
        return _transition(state, payload, seq)
    if kind == "eligibility_deferred":
        return _defer(state, payload, seq)
    raise TreasuryError(f"unknown treasury event kind {kind!r}")


def authorize_allowed(case: Case, capital: CapitalState) -> bool:
    """True when this group's cash and ratified base can cover the reimbursement."""
    return authorization_block(case, capital) is None


def authorization_block(case: Case, capital: CapitalState) -> str | None:
    """None when the case can be authorised. Otherwise a reason code."""
    if capital.group_scope != case.group_scope:
        raise TreasuryError("eligibility uses that group's capital only")
    if capital.currency != case.currency:
        raise TreasuryError("eligibility currency must match the case")
    amount = _dec(case.amount)
    capacity = (
        _dec(capital.settled)
        - _dec(capital.reserved)
        - _dec(capital.cash_floor)
        - _dec(capital.pending_obligations)
        - _dec(capital.withdrawal_fees)
        - _dec(capital.withdrawal_fx)
    )
    cash_ok = capacity >= amount and _dec(capital.withdrawable) >= amount
    base_ok = capital.ratified_base is None or amount <= _dec(capital.ratified_base)
    if cash_ok and base_ok:
        return None
    if cash_ok:
        return "above_ratified_base"
    return "insufficient_withdrawable"


def _cost(state: TreasuryState, payload: dict[str, object], seq: int) -> TreasuryState:
    _require(payload, ("cost_id", "tag", "path", "currency", "vendor", "evidence"))
    tag = str(payload["tag"])
    path = str(payload["path"])
    if tag not in SCOPES:
        raise TreasuryError("a direct cost is tagged A or B")
    if path not in PATHS:
        raise TreasuryError("cost path must be owner_paid or broker_deducted")
    amount = _money(payload.get("amount"))
    if amount <= 0:
        raise TreasuryError("cost amount must be positive")
    cost = Cost(
        cost_id=str(payload["cost_id"]),
        tag=tag,
        path=path,
        amount=_text(amount),
        currency=str(payload["currency"]),
        vendor=str(payload["vendor"]),
        evidence=str(payload["evidence"]),
    )
    _unique_cost(state, cost.cost_id)
    cases = state.cases
    if path == "owner_paid":
        _require(payload, ("reimbursement_id",))
        _unique_case(state.cases, str(payload["reimbursement_id"]))
        cases = cases + (_open_case(payload, cost.cost_id, tag, cost.amount, cost.currency),)
    return TreasuryState(
        costs=state.costs + (cost,),
        cases=cases,
        allocations=state.allocations,
        obligations=state.obligations,
        last_seq=seq,
    )


def _shared_cost(state: TreasuryState, payload: dict[str, object], seq: int) -> TreasuryState:
    _require(
        payload,
        ("cost_id", "path", "currency", "vendor", "evidence", "basis", "rule_version"),
    )
    if payload.get("tag") != "GLOBAL":
        raise TreasuryError("a shared cost is tagged GLOBAL")
    path = str(payload["path"])
    if path not in PATHS:
        raise TreasuryError("cost path must be owner_paid or broker_deducted")
    amount = _money(payload.get("amount"))
    if amount <= 0:
        raise TreasuryError("cost amount must be positive")
    shares = _shares(payload.get("shares"), amount)
    _unique_cost(state, str(payload["cost_id"]))
    cost = Cost(
        cost_id=str(payload["cost_id"]),
        tag="GLOBAL",
        path=path,
        amount=_text(amount),
        currency=str(payload["currency"]),
        vendor=str(payload["vendor"]),
        evidence=str(payload["evidence"]),
    )
    allocation = Allocation(
        cost_id=cost.cost_id,
        basis=str(payload["basis"]).strip(),
        rule_version=str(payload["rule_version"]).strip(),
        evidence=str(payload["evidence"]).strip(),
        share_a=_text(shares["A"]),
        share_b=_text(shares["B"]),
    )
    if not allocation.basis or not allocation.rule_version or not allocation.evidence:
        raise TreasuryError("allocation requires basis, rule version, and evidence")
    cases = state.cases
    if path == "owner_paid":
        raw = payload.get("shares")
        if not isinstance(raw, list):
            raise TreasuryError("allocation shares are required")
        for item in raw:
            share = shares[str(item["scope"])]
            if share == 0:
                continue
            if not isinstance(item, dict):
                raise TreasuryError("allocation share must be an object")
            _require(item, ("reimbursement_id",))
            _unique_case(cases, str(item["reimbursement_id"]))
            cases = cases + (
                _open_case(item, cost.cost_id, str(item["scope"]), _text(share), cost.currency),
            )
    return TreasuryState(
        costs=state.costs + (cost,),
        cases=cases,
        allocations=state.allocations + (allocation,),
        obligations=state.obligations,
        last_seq=seq,
    )


def _obligation(state: TreasuryState, payload: dict[str, object], seq: int) -> TreasuryState:
    _require(
        payload,
        ("obligation_id", "group_scope", "owner", "due_date", "currency", "broker_dependency"),
    )
    scope = str(payload["group_scope"])
    if scope not in SCOPES:
        raise TreasuryError("obligation scope must be one group")
    amount = _money(payload.get("amount"))
    if amount < 0:
        raise TreasuryError("obligation amount cannot be negative")
    if not isinstance(payload.get("reserve"), bool):
        raise TreasuryError("obligation reserve flag is required")
    if not isinstance(payload.get("exposure_reduction_required"), bool):
        raise TreasuryError("obligation exposure flag is required")
    item = Obligation(
        obligation_id=str(payload["obligation_id"]),
        group_scope=scope,
        owner=str(payload["owner"]),
        due_date=str(payload["due_date"]),
        currency=str(payload["currency"]),
        amount=_text(amount),
        broker_dependency=str(payload["broker_dependency"]),
        reserve=bool(payload["reserve"]),
        exposure_reduction_required=bool(payload["exposure_reduction_required"]),
    )
    return TreasuryState(
        costs=state.costs,
        cases=state.cases,
        allocations=state.allocations,
        obligations=state.obligations + (item,),
        last_seq=seq,
    )


def _transition(state: TreasuryState, payload: dict[str, object], seq: int) -> TreasuryState:
    _require(payload, ("reimbursement_id", "to_status"))
    status = str(payload["to_status"])
    if status not in STATUSES:
        raise TreasuryError(f"unknown reimbursement status {status!r}")
    case = _case(state, str(payload["reimbursement_id"]))
    if status not in _NEXT[case.status]:
        raise TreasuryError(f"cannot move {case.status} to {status}")
    matched = case.broker_matched
    if status == "BROKER_RECONCILIATION":
        _require(payload, ("broker_movement_id",))
        if not isinstance(payload.get("broker_matched"), bool):
            raise TreasuryError("broker reconciliation requires a match flag")
        matched = bool(payload["broker_matched"])
    if status == "REIMBURSED" and matched is not True:
        raise TreasuryError("reimbursement completes only after a matched broker movement")
    if status == "MISSED" and case.status == "BROKER_RECONCILIATION" and matched is True:
        raise TreasuryError("a matched broker movement is not a missed reimbursement")
    updated = replace(case, status=status, broker_matched=matched, defer_reason="")
    return _put(state, updated, seq)


def _defer(state: TreasuryState, payload: dict[str, object], seq: int) -> TreasuryState:
    _require(payload, ("reimbursement_id", "reason"))
    case = _case(state, str(payload["reimbursement_id"]))
    if case.status != "REIMBURSEMENT_ELIGIBILITY_PENDING":
        raise TreasuryError("only a pending eligibility check can be deferred")
    updated = replace(case, defer_reason=str(payload["reason"]).strip())
    if not updated.defer_reason:
        raise TreasuryError("deferral requires a reason")
    return _put(state, updated, seq)


def _open_case(
    payload: dict[str, object], cost_id: str, scope: str, amount: str, currency: str
) -> Case:
    return Case(
        reimbursement_id=str(payload["reimbursement_id"]),
        cost_id=cost_id,
        group_scope=scope,
        amount=amount,
        currency=currency,
        status="COST_RECORDED",
        broker_matched=None,
        defer_reason="",
    )


def _shares(raw: object, total: Decimal) -> dict[str, Decimal]:
    if not isinstance(raw, list) or len(raw) != 2:
        raise TreasuryError("shared cost requires one share for each group")
    found: dict[str, Decimal] = {}
    for item in raw:
        if not isinstance(item, dict):
            raise TreasuryError("allocation share must be an object")
        scope = str(item.get("scope", ""))
        if scope not in SCOPES or scope in found:
            raise TreasuryError("allocation names each group once")
        amount = _money(item.get("amount"))
        if amount < 0:
            raise TreasuryError("allocation share cannot be negative")
        found[scope] = amount
    if found["A"] + found["B"] != total:
        raise TreasuryError("allocation shares must sum to the cost")
    return found


def _unique_cost(state: TreasuryState, cost_id: str) -> None:
    if any(cost.cost_id == cost_id for cost in state.costs):
        raise TreasuryError(f"cost {cost_id} already exists")


def _unique_case(cases: tuple[Case, ...], reimbursement_id: str) -> None:
    if any(case.reimbursement_id == reimbursement_id for case in cases):
        raise TreasuryError(f"reimbursement {reimbursement_id} already exists")


def _case(state: TreasuryState, reimbursement_id: str) -> Case:
    for case in state.cases:
        if case.reimbursement_id == reimbursement_id:
            return case
    raise TreasuryError(f"reimbursement {reimbursement_id} does not exist")


def _put(state: TreasuryState, updated: Case, seq: int) -> TreasuryState:
    cases = tuple(
        updated if case.reimbursement_id == updated.reimbursement_id else case
        for case in state.cases
    )
    return TreasuryState(
        costs=state.costs,
        cases=cases,
        allocations=state.allocations,
        obligations=state.obligations,
        last_seq=seq,
    )


def _advance(state: TreasuryState, seq: int) -> TreasuryState:
    return TreasuryState(
        costs=state.costs,
        cases=state.cases,
        allocations=state.allocations,
        obligations=state.obligations,
        last_seq=seq,
    )


def _require(payload: dict[str, object], keys: tuple[str, ...]) -> None:
    for key in keys:
        if not str(payload.get(key, "")).strip():
            raise TreasuryError(f"{key} is required")


def _money(value: object) -> Decimal:
    if not isinstance(value, str) or not value.strip():
        raise TreasuryError("money values must be decimal strings")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise TreasuryError("money values must be decimal strings") from exc
    if not amount.is_finite():
        raise TreasuryError("money values must be finite")
    return amount


def _dec(value: str) -> Decimal:
    return Decimal(value)


def _text(amount: Decimal) -> str:
    text = format(amount, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
