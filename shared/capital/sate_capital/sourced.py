"""Submit capital events to the fact log, then project them."""

from __future__ import annotations

from sate_factlog.log import FactLog

from sate_capital.ledger import CapitalState, apply_event, project

_WRITER = "capital"


def submit_snapshot(
    log: FactLog,
    state: CapitalState,
    payload: dict[str, object],
    **identity: str,
) -> CapitalState:
    body = {"kind": "snapshot", **payload}
    return _commit(
        log, state, body, event_type="broker_balances", writer_id="kernel-a", **identity
    )


def submit_bind(
    log: FactLog,
    state: CapitalState,
    ratified_base: str,
    **identity: str,
) -> CapitalState:
    body = {"kind": "bind_rcb", "ratified_base": ratified_base}
    return _commit(log, state, body, event_type="capital_state", **identity)


def submit_withdrawal(
    log: FactLog,
    state: CapitalState,
    payload: dict[str, object],
    **identity: str,
) -> CapitalState:
    body = {"kind": "withdrawal", **payload}
    return _commit(log, state, body, event_type="capital_state", **identity)


def submit_deposit(
    log: FactLog,
    state: CapitalState,
    payload: dict[str, object],
    **identity: str,
) -> CapitalState:
    body = {"kind": "deposit", **payload}
    return _commit(log, state, body, event_type="capital_state", **identity)


def submit_adjustment(
    log: FactLog,
    state: CapitalState,
    payload: dict[str, object],
    **identity: str,
) -> CapitalState:
    body = {"kind": "adjustment", **payload}
    return _commit(
        log, state, body, event_type="capital_state", writer_id="control-api", **identity
    )


def submit_fill_fees(
    log: FactLog,
    state: CapitalState,
    payload: dict[str, object],
    **identity: str,
) -> CapitalState:
    body = {"kind": "fill_fees", **payload}
    return _commit(log, state, body, event_type="capital_state", **identity)


def submit_swap_accrual(
    log: FactLog,
    state: CapitalState,
    payload: dict[str, object],
    **identity: str,
) -> CapitalState:
    body = {"kind": "swap_accrual", **payload}
    return _commit(log, state, body, event_type="capital_state", **identity)


def submit_obligation(
    log: FactLog,
    state: CapitalState,
    payload: dict[str, object],
    **identity: str,
) -> CapitalState:
    body = {"kind": "obligation", **payload}
    return _commit(log, state, body, event_type="capital_state", **identity)


def replay(log: FactLog, scope: str) -> CapitalState:
    records = log.poll(after_seq=0, group_scope=scope, reader_id=_WRITER)
    return project(scope, records)


def _commit(
    log: FactLog,
    state: CapitalState,
    payload: dict[str, object],
    *,
    event_type: str,
    event_id: str,
    occurred_at: str,
    recorded_at: str,
    correlation_id: str,
    writer_id: str = "capital",
) -> CapitalState:
    body = dict(payload)
    body["group_id"] = state.group_scope
    prior = _existing(log, state.group_scope, event_id)
    if prior is not None:
        if prior.seq <= state.last_seq:
            return state
        return apply_event(state, prior.payload, seq=prior.seq)
    apply_event(state, body, seq=state.last_seq + 1)
    record = log.append(
        event_id=event_id,
        event_type=event_type,
        group_scope=state.group_scope,
        occurred_at=occurred_at,
        recorded_at=recorded_at,
        correlation_id=correlation_id,
        writer_id=writer_id,
        payload=body,
    )
    return apply_event(state, record.payload, seq=record.seq)


def _existing(log: FactLog, scope: str, event_id: str):
    for record in log.poll(after_seq=0, group_scope=scope, reader_id=_WRITER):
        if record.event_id == event_id:
            return record
    return None
