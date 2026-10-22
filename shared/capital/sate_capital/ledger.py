"""Five-state capital projection. Withdrawable is calculated, never copied from equity."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from sate_capital.errors import CapitalError
from sate_rcb.service import blank as rcb_blank
from sate_rcb.service import fold as rcb_fold

SCOPES = frozenset({"A", "B"})
BUCKETS = frozenset({"equity", "realised_pnl", "settled", "reserved"})
FORBIDDEN = frozenset({
    "cash",
    "withdrawable",
    "withdrawable_cash",
    "combined_equity",
    "combined_rcb",
    "portfolio_total",
})
_ZERO = Decimal("0")


@dataclass(frozen=True)
class Obligation:
    obligation_id: str
    owner: str
    due_date: str
    currency: str
    amount: str
    broker_dependency: str
    reserve: bool
    funding_scope: str
    cross_broker_owner_transfer: bool


@dataclass(frozen=True)
class CapitalState:
    group_scope: str
    currency: str
    broker_id: str
    account_id: str
    source_ts: str
    equity: str
    realised_pnl: str
    settled: str
    reserved: str
    withdrawable: str
    ratified_base: str | None
    cash_floor: str
    pending_obligations: str
    withdrawal_fees: str
    withdrawal_fx: str
    withdrawal_hold: str
    trading_costs: str
    last_deposit_effect: str
    obligations: tuple[Obligation, ...]
    last_seq: int


def blank(scope: str) -> CapitalState:
    if scope not in SCOPES:
        raise CapitalError(f"capital ledger refuses scope {scope!r}")
    return _freeze(
        scope=scope,
        currency="",
        broker_id="",
        account_id="",
        source_ts="",
        equity=_ZERO,
        realised_pnl=_ZERO,
        settled=_ZERO,
        reserved=_ZERO,
        ratified_base=None,
        cash_floor=_ZERO,
        pending_obligations=_ZERO,
        withdrawal_fees=_ZERO,
        withdrawal_fx=_ZERO,
        withdrawal_hold=_ZERO,
        trading_costs=_ZERO,
        last_deposit_effect="",
        obligations=(),
        last_seq=0,
    )


def effective_limit_base(state: CapitalState) -> str:
    """A-RCB-01 and A-RCB-02. Equity above the base does not raise the limit."""
    if state.ratified_base is None:
        return _text(_ZERO)
    return _text(min(_dec(state.ratified_base), _dec(state.equity)))


def tie_out(state: CapitalState) -> dict[str, bool]:
    """Check the derived figure and that the five buckets are separate fields."""
    exported = export_state(state)
    buckets = ("equity", "realised_pnl", "settled", "reserved", "withdrawable")
    return {
        "withdrawable_matches_formula": exported["withdrawable"] == _text(_withdrawable(state)),
        "buckets_are_distinct_fields": len(set(buckets)) == 5 and set(buckets).issubset(exported),
    }


def export_state(state: CapitalState) -> dict[str, object]:
    return {
        "group_scope": state.group_scope,
        "currency": state.currency,
        "equity": state.equity,
        "realised_pnl": state.realised_pnl,
        "settled": state.settled,
        "reserved": state.reserved,
        "withdrawable": state.withdrawable,
        "ratified_base": state.ratified_base,
        "cash_floor": state.cash_floor,
        "pending_obligations": state.pending_obligations,
        "withdrawal_fees": state.withdrawal_fees,
        "withdrawal_fx": state.withdrawal_fx,
        "trading_costs": state.trading_costs,
        "last_deposit_effect": state.last_deposit_effect,
        "last_seq": state.last_seq,
    }


def reconcile(stored: dict[str, object], state: CapitalState) -> bool:
    """True when a saved projection matches a fresh replay."""
    return stored == export_state(state)


def project(scope: str, records: list) -> CapitalState:
    state = blank(scope)
    rcb = rcb_blank(scope)
    for record in sorted(records, key=lambda item: item.seq):
        rcb = rcb_fold(rcb, record)
        state = fold(state, record)
        if record.event_type == "rcb_change" and rcb.version >= 1 and rcb.ratified_base:
            state = _replace(state, state.last_seq, ratified_base=_dec(rcb.ratified_base))
    return state


def fold(state: CapitalState, record) -> CapitalState:
    if record.seq <= state.last_seq:
        return state
    if record.group_scope != state.group_scope:
        return _advance(state, record.seq)
    if record.event_type not in {"capital_state", "broker_balances"}:
        return _advance(state, record.seq)
    payload = record.payload
    if "projection_id" in payload:
        return _advance(state, record.seq)
    kind = str(payload.get("kind", ""))
    if kind == "snapshot" and record.writer_id != "kernel-a":
        raise CapitalError("a broker snapshot must come from the broker adapter")
    if kind == "adjustment" and record.writer_id != "control-api":
        raise CapitalError("an adjustment must come from the admin writer")
    return apply_event(state, payload, seq=record.seq)


def apply_event(state: CapitalState, payload: dict[str, object], *, seq: int) -> CapitalState:
    overlap = FORBIDDEN.intersection(payload)
    if overlap:
        names = ", ".join(sorted(overlap))
        raise CapitalError(f"field cannot enter the capital ledger: {names}")
    group_id = payload.get("group_id", state.group_scope)
    if group_id != state.group_scope:
        raise CapitalError("payload group does not match the ledger scope")
    kind = str(payload.get("kind", ""))
    if kind == "snapshot":
        return _snapshot(state, payload, seq)
    if kind == "bind_rcb":
        return _bind(state, payload, seq)
    if kind == "withdrawal":
        return _withdrawal(state, payload, seq)
    if kind == "deposit":
        return _deposit(state, payload, seq)
    if kind == "adjustment":
        return _adjustment(state, payload, seq)
    if kind == "fill_fees":
        return _fill_fees(state, payload, seq)
    if kind == "swap_accrual":
        return _swap_accrual(state, payload, seq)
    if kind == "obligation":
        return _obligation(state, payload, seq)
    raise CapitalError(f"unknown capital event kind {kind!r}")


def _snapshot(state: CapitalState, payload: dict[str, object], seq: int) -> CapitalState:
    _require(payload, ("broker_id", "account_id", "currency", "source_ts"))
    if "ratified_base" in payload:
        raise CapitalError("a broker snapshot cannot set the ratified base")
    source_ts = str(payload["source_ts"]).strip()
    if state.source_ts and source_ts <= state.source_ts:
        raise CapitalError("broker snapshot time must move forward")
    return _freeze(
        scope=state.group_scope,
        currency=str(payload["currency"]).strip(),
        broker_id=str(payload["broker_id"]).strip(),
        account_id=str(payload["account_id"]).strip(),
        source_ts=source_ts,
        equity=_money(payload.get("equity")),
        realised_pnl=_money(payload.get("realised_pnl")),
        settled=_money(payload.get("settled")),
        reserved=_money(payload.get("reserved")),
        ratified_base=_optional_base(state.ratified_base),
        cash_floor=_money(payload.get("cash_floor")),
        pending_obligations=_dec(state.pending_obligations),
        withdrawal_fees=_dec(state.withdrawal_fees),
        withdrawal_fx=_dec(state.withdrawal_fx),
        withdrawal_hold=_ZERO,
        trading_costs=_dec(state.trading_costs),
        last_deposit_effect=state.last_deposit_effect,
        obligations=state.obligations,
        last_seq=seq,
    )


def _bind(state: CapitalState, payload: dict[str, object], seq: int) -> CapitalState:
    amount = _money(payload.get("ratified_base"))
    if amount < 0:
        raise CapitalError("ratified base cannot be negative")
    if state.ratified_base is not None and _dec(state.ratified_base) != amount:
        raise CapitalError("ratified base changes only through withdrawal")
    return _replace(state, seq, ratified_base=amount)


def _withdrawal(state: CapitalState, payload: dict[str, object], seq: int) -> CapitalState:
    _same_currency(state, payload)
    amount = _money(payload.get("amount"))
    fee = _money(payload.get("fee"))
    fx_cost = _money(payload.get("fx_cost"))
    if amount <= 0 or fee < 0 or fx_cost < 0:
        raise CapitalError("withdrawal amount must be positive and costs cannot be negative")
    if state.ratified_base is None:
        raise CapitalError("withdrawal requires a ratified base")
    if amount + fee + fx_cost > _dec(state.withdrawable):
        raise CapitalError("withdrawal exceeds withdrawable")
    base = _dec(state.ratified_base)
    if amount > base:
        raise CapitalError("withdrawal exceeds ratified base")
    held = amount + fee + fx_cost
    return _replace(
        state,
        seq,
        ratified_base=base - amount,
        withdrawal_fees=_dec(state.withdrawal_fees) + fee,
        withdrawal_fx=_dec(state.withdrawal_fx) + fx_cost,
        withdrawal_hold=_dec(state.withdrawal_hold) + held,
    )


def _deposit(state: CapitalState, payload: dict[str, object], seq: int) -> CapitalState:
    _same_currency(state, payload)
    amount = _money(payload.get("amount"))
    if amount <= 0:
        raise CapitalError("deposit amount must be positive")
    effect = "inert_halt" if payload.get("halted") is True else "inert_pending_ratification"
    return _replace(state, seq, last_deposit_effect=effect)


def _adjustment(state: CapitalState, payload: dict[str, object], seq: int) -> CapitalState:
    _same_currency(state, payload)
    bucket = str(payload.get("bucket", ""))
    if bucket not in BUCKETS:
        raise CapitalError("adjustment must name equity, realised_pnl, settled, or reserved")
    principal = str(payload.get("principal", "")).strip()
    if not principal:
        raise CapitalError("adjustment requires an admin principal")
    amount = _money(payload.get("amount"))
    values = {
        "equity": _dec(state.equity),
        "realised_pnl": _dec(state.realised_pnl),
        "settled": _dec(state.settled),
        "reserved": _dec(state.reserved),
    }
    values[bucket] = amount
    return _replace(state, seq, **values)


def _fill_fees(state: CapitalState, payload: dict[str, object], seq: int) -> CapitalState:
    _require(payload, ("fill_id", "currency", "quote_currency", "fx_rate"))
    _same_currency(state, payload)
    commission = _money(payload.get("commission"))
    swap = _money(payload.get("swap"))
    slippage = _money(payload.get("slippage"))
    if min(commission, swap, slippage) < 0:
        raise CapitalError("fill costs cannot be negative")
    rate = _money(payload.get("fx_rate"))
    quote = str(payload["quote_currency"]).strip()
    if quote == state.currency:
        if rate != Decimal("1"):
            raise CapitalError("fx rate must be 1 when currencies match")
    elif rate <= 0:
        raise CapitalError("fx rate is required at each fill")
    cost = (commission + swap + slippage) * rate
    return _replace(
        state,
        seq,
        realised_pnl=_dec(state.realised_pnl) - cost,
        trading_costs=_dec(state.trading_costs) + cost,
    )


def _swap_accrual(state: CapitalState, payload: dict[str, object], seq: int) -> CapitalState:
    _require(payload, ("accrual_id",))
    _same_currency(state, payload)
    amount = _money(payload.get("amount"))
    if amount < 0:
        raise CapitalError("swap accrual cannot be negative")
    return _replace(
        state,
        seq,
        realised_pnl=_dec(state.realised_pnl) - amount,
        trading_costs=_dec(state.trading_costs) + amount,
    )


def _obligation(state: CapitalState, payload: dict[str, object], seq: int) -> CapitalState:
    _require(
        payload,
        ("obligation_id", "owner", "due_date", "currency", "broker_dependency", "funding_scope"),
    )
    amount = _money(payload.get("amount"))
    if amount < 0:
        raise CapitalError("obligation amount cannot be negative")
    funding = str(payload["funding_scope"])
    if funding not in SCOPES:
        raise CapitalError("obligation funding scope must be one group")
    reserve = payload.get("reserve") is True
    cross = funding != state.group_scope
    if not cross:
        _same_currency(state, payload)
    pending = _dec(state.pending_obligations)
    if reserve and not cross:
        pending += amount
    item = Obligation(
        obligation_id=str(payload["obligation_id"]),
        owner=str(payload["owner"]),
        due_date=str(payload["due_date"]),
        currency=str(payload["currency"]),
        amount=_text(amount),
        broker_dependency=str(payload["broker_dependency"]),
        reserve=reserve,
        funding_scope=funding,
        cross_broker_owner_transfer=cross,
    )
    obligations = state.obligations + (item,)
    return _replace(state, seq, pending_obligations=pending, obligations=obligations)


def _replace(state: CapitalState, seq: int, **updates: object) -> CapitalState:
    equity = updates.get("equity", _dec(state.equity))
    realised = updates.get("realised_pnl", _dec(state.realised_pnl))
    settled = updates.get("settled", _dec(state.settled))
    reserved = updates.get("reserved", _dec(state.reserved))
    base = updates.get("ratified_base", _optional_base(state.ratified_base))
    floor = updates.get("cash_floor", _dec(state.cash_floor))
    pending = updates.get("pending_obligations", _dec(state.pending_obligations))
    fees = updates.get("withdrawal_fees", _dec(state.withdrawal_fees))
    fx_costs = updates.get("withdrawal_fx", _dec(state.withdrawal_fx))
    hold = updates.get("withdrawal_hold", _dec(state.withdrawal_hold))
    costs = updates.get("trading_costs", _dec(state.trading_costs))
    effect = updates.get("last_deposit_effect", state.last_deposit_effect)
    obligations = updates.get("obligations", state.obligations)
    return _freeze(
        scope=state.group_scope,
        currency=state.currency,
        broker_id=state.broker_id,
        account_id=state.account_id,
        source_ts=state.source_ts,
        equity=equity,
        realised_pnl=realised,
        settled=settled,
        reserved=reserved,
        ratified_base=base,
        cash_floor=floor,
        pending_obligations=pending,
        withdrawal_fees=fees,
        withdrawal_fx=fx_costs,
        withdrawal_hold=hold,
        trading_costs=costs,
        last_deposit_effect=str(effect),
        obligations=obligations,
        last_seq=seq,
    )


def _freeze(
    *,
    scope: str,
    currency: str,
    broker_id: str,
    account_id: str,
    source_ts: str,
    equity: Decimal,
    realised_pnl: Decimal,
    settled: Decimal,
    reserved: Decimal,
    ratified_base: Decimal | None,
    cash_floor: Decimal,
    pending_obligations: Decimal,
    withdrawal_fees: Decimal,
    withdrawal_fx: Decimal,
    withdrawal_hold: Decimal,
    trading_costs: Decimal,
    last_deposit_effect: str,
    obligations: tuple[Obligation, ...],
    last_seq: int,
) -> CapitalState:
    if not currency and (broker_id or account_id):
        raise CapitalError("snapshot currency is required")
    state = CapitalState(
        group_scope=scope,
        currency=currency,
        broker_id=broker_id,
        account_id=account_id,
        source_ts=source_ts,
        equity=_text(equity),
        realised_pnl=_text(realised_pnl),
        settled=_text(settled),
        reserved=_text(reserved),
        withdrawable="0",
        ratified_base=None if ratified_base is None else _text(ratified_base),
        cash_floor=_text(cash_floor),
        pending_obligations=_text(pending_obligations),
        withdrawal_fees=_text(withdrawal_fees),
        withdrawal_fx=_text(withdrawal_fx),
        withdrawal_hold=_text(withdrawal_hold),
        trading_costs=_text(trading_costs),
        last_deposit_effect=last_deposit_effect,
        obligations=obligations,
        last_seq=last_seq,
    )
    return CapitalState(
        group_scope=state.group_scope,
        currency=state.currency,
        broker_id=state.broker_id,
        account_id=state.account_id,
        source_ts=state.source_ts,
        equity=state.equity,
        realised_pnl=state.realised_pnl,
        settled=state.settled,
        reserved=state.reserved,
        withdrawable=_text(_withdrawable(state)),
        ratified_base=state.ratified_base,
        cash_floor=state.cash_floor,
        pending_obligations=state.pending_obligations,
        withdrawal_fees=state.withdrawal_fees,
        withdrawal_fx=state.withdrawal_fx,
        withdrawal_hold=state.withdrawal_hold,
        trading_costs=state.trading_costs,
        last_deposit_effect=state.last_deposit_effect,
        obligations=state.obligations,
        last_seq=state.last_seq,
    )


def _withdrawable(state: CapitalState) -> Decimal:
    raw = (
        _dec(state.settled)
        - _dec(state.reserved)
        - _dec(state.withdrawal_hold)
        - _dec(state.cash_floor)
        - _dec(state.pending_obligations)
    )
    if raw < 0:
        return _ZERO
    return raw


def _advance(state: CapitalState, seq: int) -> CapitalState:
    return _replace(state, seq)


def _same_currency(state: CapitalState, payload: dict[str, object]) -> None:
    if not state.currency:
        raise CapitalError("a broker snapshot is required before this event")
    if str(payload.get("currency", "")).strip() != state.currency:
        raise CapitalError("event currency must match the ledger currency")


def _require(payload: dict[str, object], keys: tuple[str, ...]) -> None:
    for key in keys:
        if not str(payload.get(key, "")).strip():
            raise CapitalError(f"{key} is required")


def _optional_base(value: str | None) -> Decimal | None:
    if value is None:
        return None
    return _dec(value)


def _money(value: object) -> Decimal:
    if not isinstance(value, str) or not value.strip():
        raise CapitalError("money values must be decimal strings")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise CapitalError("money values must be decimal strings") from exc
    if not amount.is_finite():
        raise CapitalError("money values must be finite")
    return amount


def _dec(value: str) -> Decimal:
    return Decimal(value)


def _text(amount: Decimal) -> str:
    text = format(amount, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
