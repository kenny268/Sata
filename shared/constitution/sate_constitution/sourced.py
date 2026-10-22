"""Submit constitution events to the fact log, then project them."""

from __future__ import annotations

from sate_factlog.log import FactLog

from sate_constitution.document import classify, hours_are_placeholder
from sate_constitution.errors import ConstitutionError
from sate_constitution.service import (
    ConstitutionState,
    active_document,
    active_version,
    apply_event,
    project,
    trade_gate,
)
from sate_constitution.signing import signature_valid

_WRITER = "constitution"
_POLLED = ("A", "B", "GLOBAL")


def submit_activate(
    log: FactLog,
    state: ConstitutionState,
    envelope: dict[str, object],
    *,
    public_key: bytes,
    key_id: str,
    now: str,
    **identity: str,
) -> ConstitutionState:
    _check(envelope, public_key, key_id, now)
    body = {
        "kind": "activate",
        "activated_at": now,
        "predecessor_version": active_version(state),
        "envelope": envelope,
    }
    occurred_at = identity.pop("occurred_at", now)
    return _commit(
        log,
        state,
        body,
        public_key=public_key,
        key_id=key_id,
        occurred_at=occurred_at,
        **identity,
    )


def submit_propose(
    log: FactLog,
    state: ConstitutionState,
    envelope: dict[str, object],
    *,
    public_key: bytes,
    key_id: str,
    now: str,
    reason: str,
    **identity: str,
) -> ConstitutionState:
    _check(envelope, public_key, key_id, now)
    current = active_document(state)
    if current is None:
        raise ConstitutionError("activate the first version before proposing an edit", code="version")
    change_class = classify(current, envelope["document"])
    if change_class == "lock_hours":
        lock_hours: int | None = 0
    elif hours_are_placeholder(current):
        lock_hours = None
    elif change_class == "tighten":
        lock_hours = int(current["meta"]["tighten_lock_hours"])
    else:
        lock_hours = int(current["meta"]["loosen_lock_hours"])
    if not reason.strip():
        raise ConstitutionError("a proposal needs a change reason", code="reason")
    body = {
        "kind": "propose",
        "proposed_at": now,
        "change_class": change_class,
        "lock_hours": lock_hours,
        "reason": reason.strip(),
        "envelope": envelope,
    }
    occurred_at = identity.pop("occurred_at", now)
    return _commit(
        log,
        state,
        body,
        public_key=public_key,
        key_id=key_id,
        occurred_at=occurred_at,
        **identity,
    )


def submit_emergency(
    log: FactLog,
    state: ConstitutionState,
    envelope: dict[str, object],
    *,
    public_key: bytes,
    key_id: str,
    now: str,
    pre_mortem: str,
    **identity: str,
) -> ConstitutionState:
    _check(envelope, public_key, key_id, now)
    if not pre_mortem.strip():
        raise ConstitutionError("emergency tightening needs a pre-mortem", code="pre_mortem")
    body = {
        "kind": "emergency",
        "activated_at": now,
        "predecessor_version": active_version(state),
        "pre_mortem": pre_mortem.strip(),
        "envelope": envelope,
    }
    occurred_at = identity.pop("occurred_at", now)
    return _commit(
        log,
        state,
        body,
        public_key=public_key,
        key_id=key_id,
        occurred_at=occurred_at,
        **identity,
    )


def replay(log: FactLog, scope: str, *, public_key: bytes, key_id: str) -> ConstitutionState:
    records = []
    for group in _POLLED:
        records.extend(log.poll(after_seq=0, group_scope=group, reader_id=_WRITER))
    return project(scope, records, public_key=public_key, key_id=key_id)


def _check(envelope: dict[str, object], public_key: bytes, key_id: str, now: str) -> None:
    trade_gate(envelope, public_key, key_id, now)
    if not signature_valid(envelope, public_key):
        raise ConstitutionError("constitution signature is invalid", code="signature")


def _commit(
    log: FactLog,
    state: ConstitutionState,
    payload: dict[str, object],
    *,
    public_key: bytes,
    key_id: str,
    event_id: str,
    occurred_at: str,
    recorded_at: str,
    correlation_id: str,
) -> ConstitutionState:
    for group in _POLLED:
        for record in log.poll(after_seq=0, group_scope=group, reader_id=_WRITER):
            if record.event_id == event_id:
                return replay(log, state.group_scope, public_key=public_key, key_id=key_id)
    apply_event(state, payload, seq=state.seq + 1)
    log.append(
        event_id=event_id,
        event_type="constitution",
        group_scope=state.group_scope,
        occurred_at=occurred_at,
        recorded_at=recorded_at,
        correlation_id=correlation_id,
        writer_id=_WRITER,
        payload=payload,
    )
    return replay(log, state.group_scope, public_key=public_key, key_id=key_id)
