"""Submit RCB changes to the fact log, then project them."""

from __future__ import annotations

from decimal import Decimal

from sate_capital.ledger import CapitalState
from sate_factlog.log import FactLog

from sate_rcb.errors import RcbError
from sate_rcb.service import RcbState, apply_event, project

_WRITER = "rcb"
_POLLED = ("A", "B", "GLOBAL")


def submit_bind(
    log: FactLog,
    state: RcbState,
    ratified_base: str,
    *,
    passkey_assertion: str,
    **identity: str,
) -> RcbState:
    body = {
        "kind": "bind",
        "ratified_base": ratified_base,
        "passkey_assertion": passkey_assertion,
    }
    return _commit(log, state, body, **identity)


def submit_deposit(
    log: FactLog,
    state: RcbState,
    amount: str,
    **identity: str,
) -> RcbState:
    body = {"kind": "deposit", "amount": amount, "occurred_at": identity["occurred_at"]}
    return _commit(log, state, body, **identity)


def submit_propose(
    log: FactLog,
    state: RcbState,
    new_base: str,
    **identity: str,
) -> RcbState:
    body = {"kind": "propose", "new_base": new_base, "occurred_at": identity["occurred_at"]}
    return _commit(log, state, body, **identity)


def submit_halt(
    log: FactLog,
    state: RcbState,
    level: str,
    **identity: str,
) -> RcbState:
    body = {"kind": "halt", "level": level, "occurred_at": identity["occurred_at"]}
    return _commit(log, state, body, **identity)


def submit_halt_clear(log: FactLog, state: RcbState, **identity: str) -> RcbState:
    return _commit(log, state, {"kind": "halt_clear"}, **identity)


def submit_withdrawal(
    log: FactLog,
    state: RcbState,
    capital: CapitalState,
    payload: dict[str, object],
    **identity: str,
) -> RcbState:
    if capital.group_scope != state.group_scope:
        raise RcbError("capital scope does not match RCB")
    currency = payload.get("currency")
    if currency != capital.currency:
        raise RcbError("withdrawal currency does not match the capital ledger")
    amount = Decimal(str(payload["amount"]))
    fee = Decimal(str(payload["fee"]))
    fx_cost = Decimal(str(payload["fx_cost"]))
    if amount + fee + fx_cost > Decimal(capital.withdrawable):
        raise RcbError("withdrawal exceeds withdrawable")
    body = {
        "kind": "withdrawal",
        "amount": payload["amount"],
        "fee": payload["fee"],
        "fx_cost": payload["fx_cost"],
        "currency": currency,
    }
    return _commit(log, state, body, **identity)


def submit_ratify(
    log: FactLog,
    state: RcbState,
    *,
    passkey_assertion: str,
    ratified_at: str,
    event_id: str,
    recorded_at: str,
    correlation_id: str,
) -> RcbState:
    body = {
        "kind": "ratify",
        "passkey_assertion": passkey_assertion,
        "ratified_at": ratified_at,
        "clean_since": state.clean_since or "",
        "previous_base": state.ratified_base or "",
        "new_base": state.proposed_base or "",
    }
    return _commit(
        log,
        state,
        body,
        event_id=event_id,
        occurred_at=ratified_at,
        recorded_at=recorded_at,
        correlation_id=correlation_id,
    )


def replay(log: FactLog, scope: str) -> RcbState:
    records = []
    for group in _POLLED:
        records.extend(log.poll(after_seq=0, group_scope=group, reader_id=_WRITER))
    return project(scope, records)


def _commit(
    log: FactLog,
    state: RcbState,
    payload: dict[str, object],
    *,
    event_id: str,
    occurred_at: str,
    recorded_at: str,
    correlation_id: str,
) -> RcbState:
    for group in _POLLED:
        for record in log.poll(after_seq=0, group_scope=group, reader_id=_WRITER):
            if record.event_id == event_id:
                return replay(log, state.group_scope)
    apply_event(state, payload, seq=state.seq + 1)
    log.append(
        event_id=event_id,
        event_type="rcb_change",
        group_scope=state.group_scope,
        occurred_at=occurred_at,
        recorded_at=recorded_at,
        correlation_id=correlation_id,
        writer_id=_WRITER,
        payload=payload,
    )
    return replay(log, state.group_scope)
