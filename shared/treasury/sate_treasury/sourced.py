"""Submit treasury events to the fact log, then project them."""

from __future__ import annotations

from sate_capital.ledger import CapitalState
from sate_factlog.log import FactLog

from sate_treasury.errors import TreasuryError
from sate_treasury.ledger import (
    TreasuryState,
    apply_event,
    authorization_block,
    project,
)

_WRITER = "treasury"
_SCOPES = ("A", "B", "GLOBAL")


def submit_cost(
    log: FactLog,
    state: TreasuryState,
    payload: dict[str, object],
    **identity: str,
) -> TreasuryState:
    body = {"kind": "cost", **payload}
    scope = str(body.get("tag", ""))
    return _commit(log, state, body, event_type="invoice", group_scope=scope, **identity)


def submit_shared_cost(
    log: FactLog,
    state: TreasuryState,
    payload: dict[str, object],
    **identity: str,
) -> TreasuryState:
    body = {"kind": "shared_cost", "tag": "GLOBAL", **payload}
    return _commit(log, state, body, event_type="invoice", group_scope="GLOBAL", **identity)


def submit_obligation(
    log: FactLog,
    state: TreasuryState,
    payload: dict[str, object],
    **identity: str,
) -> TreasuryState:
    body = {"kind": "obligation", **payload}
    scope = str(body.get("group_scope", ""))
    return _commit(log, state, body, event_type="invoice", group_scope=scope, **identity)


def submit_transition(
    log: FactLog,
    state: TreasuryState,
    payload: dict[str, object],
    **identity: str,
) -> TreasuryState:
    body = {"kind": "transition", **payload}
    case = _case_scope(state, str(body.get("reimbursement_id", "")))
    return _commit(log, state, body, event_type="reimbursement", group_scope=case, **identity)


def submit_authorize(
    log: FactLog,
    state: TreasuryState,
    reimbursement_id: str,
    capital: CapitalState,
    **identity: str,
) -> TreasuryState:
    case = _find(state, reimbursement_id)
    reason = authorization_block(case, capital)
    if reason is None:
        body = {"kind": "transition", "reimbursement_id": reimbursement_id}
        body["to_status"] = "REIMBURSEMENT_AUTHORIZED"
    else:
        body = {
            "kind": "eligibility_deferred",
            "reimbursement_id": reimbursement_id,
            "reason": reason,
        }
    return _commit(
        log,
        state,
        body,
        event_type="reimbursement",
        group_scope=case.group_scope,
        **identity,
    )


def replay(log: FactLog) -> TreasuryState:
    records = []
    for scope in _SCOPES:
        records.extend(log.poll(after_seq=0, group_scope=scope, reader_id=_WRITER))
    return project(records)


def _commit(
    log: FactLog,
    state: TreasuryState,
    payload: dict[str, object],
    *,
    event_type: str,
    group_scope: str,
    event_id: str,
    occurred_at: str,
    recorded_at: str,
    correlation_id: str,
) -> TreasuryState:
    apply_event(state, payload, seq=state.last_seq + 1)
    record = log.append(
        event_id=event_id,
        event_type=event_type,
        group_scope=group_scope,
        occurred_at=occurred_at,
        recorded_at=recorded_at,
        correlation_id=correlation_id,
        writer_id=_WRITER,
        payload=payload,
    )
    return apply_event(state, record.payload, seq=record.seq)


def _case_scope(state: TreasuryState, reimbursement_id: str) -> str:
    return _find(state, reimbursement_id).group_scope


def _find(state: TreasuryState, reimbursement_id: str):
    for case in state.cases:
        if case.reimbursement_id == reimbursement_id:
            return case
    raise TreasuryError(f"reimbursement {reimbursement_id} does not exist")
