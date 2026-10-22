"""One active constitution per environment. Pending edits stay visible until activated."""

from __future__ import annotations

import json
from dataclasses import dataclass

from sate_constitution.document import (
    add_hours,
    changed_paths,
    classify,
    hours_are_placeholder,
    live_blockers,
    lock_hours_are_ordered,
    validate_envelope,
    window_open,
)
from sate_constitution.errors import ConstitutionError
from sate_constitution.signing import signature_valid

_WRITER = "constitution"


@dataclass(frozen=True)
class Pending:
    version: int
    proposed_at: str
    change_class: str
    lock_hours: int | None
    reason: str
    paths: tuple[str, ...]
    envelope_json: str


@dataclass(frozen=True)
class ConstitutionState:
    group_scope: str
    active_json: str | None
    predecessor_version: int | None
    activated_at: str | None
    last_pre_mortem: str | None
    pending: tuple[Pending, ...]
    seq: int


def blank(scope: str) -> ConstitutionState:
    if scope not in {"A", "B"}:
        raise ConstitutionError(f"constitution refuses scope {scope!r}", code="scope")
    return ConstitutionState(
        group_scope=scope,
        active_json=None,
        predecessor_version=None,
        activated_at=None,
        last_pre_mortem=None,
        pending=(),
        seq=0,
    )


def active_document(state: ConstitutionState) -> dict[str, object] | None:
    if state.active_json is None:
        return None
    return json.loads(state.active_json)["document"]


def active_version(state: ConstitutionState) -> int | None:
    if state.active_json is None:
        return None
    return int(json.loads(state.active_json)["version"])


def view(state: ConstitutionState) -> dict[str, object]:
    document = active_document(state)
    blockers = live_blockers(document)
    return {
        "group_scope": state.group_scope,
        "active_version": active_version(state),
        "predecessor_version": state.predecessor_version,
        "last_pre_mortem": state.last_pre_mortem,
        "live_permitted": not blockers,
        "live_blockers": blockers,
        "pending": [_pending_row(item) for item in state.pending],
        "read_only": True,
    }


def trade_gate(
    envelope: dict[str, object],
    public_key: bytes,
    key_id: str,
    now: str,
    expected_version: int | None = None,
) -> int:
    """Verify the artifact for a trade. There is no per-trade approval argument."""
    _verify(envelope, public_key, key_id, now)
    version = int(envelope["version"])
    if expected_version is not None and version != expected_version:
        raise ConstitutionError("constitution version is not pinned", code="version")
    return version


def project(
    scope: str,
    records: list,
    *,
    public_key: bytes,
    key_id: str,
) -> ConstitutionState:
    state = blank(scope)
    for record in sorted(records, key=lambda item: item.seq):
        state = fold(state, record, public_key=public_key, key_id=key_id)
    return state


def fold(state: ConstitutionState, record, *, public_key: bytes, key_id: str) -> ConstitutionState:
    if record.seq <= state.seq:
        return state
    if record.group_scope == "GLOBAL" and record.event_type == "constitution":
        raise ConstitutionError("constitution cannot use a pooled scope", code="pooled")
    if record.group_scope != state.group_scope or record.event_type != "constitution":
        return _advance(state, record.seq)
    if record.writer_id != _WRITER:
        raise ConstitutionError(
            "constitution events are written by the constitution service",
            code="writer",
        )
    envelope = record.payload.get("envelope", {})
    if not isinstance(envelope, dict) or envelope.get("key_id") != key_id:
        raise ConstitutionError("constitution key id is not pinned", code="key_id")
    if not signature_valid(envelope, public_key):
        raise ConstitutionError("constitution signature is invalid", code="signature")
    return apply_event(state, record.payload, record.seq)


def apply_event(state: ConstitutionState, payload: dict[str, object], seq: int) -> ConstitutionState:
    kind = str(payload.get("kind", ""))
    if kind == "propose":
        return _propose(state, payload, seq)
    if kind == "activate":
        return _activate(state, payload, seq)
    if kind == "emergency":
        return _emergency(state, payload, seq)
    raise ConstitutionError(f"unknown constitution kind {kind!r}", code="malformed")


def _propose(state: ConstitutionState, payload: dict[str, object], seq: int) -> ConstitutionState:
    if state.pending:
        raise ConstitutionError("a proposal is already pending", code="pending")
    envelope = _envelope(payload)
    _same_scope(state, envelope)
    current = active_document(state)
    if current is None:
        raise ConstitutionError("activate the first version before proposing an edit", code="version")
    change_class = classify(current, envelope["document"])
    proposed_at = str(payload["proposed_at"])
    lock_hours = _lock_hours(current, envelope["document"], change_class)
    reason = _text(payload.get("reason"), "a proposal needs a change reason", "reason")
    if payload.get("change_class") != change_class or payload.get("lock_hours") != lock_hours:
        raise ConstitutionError("proposal lock does not match the active constitution", code="time_lock")
    pending = Pending(
        version=int(envelope["version"]),
        proposed_at=proposed_at,
        change_class=change_class,
        lock_hours=lock_hours,
        reason=reason,
        paths=changed_paths(current, envelope["document"]),
        envelope_json=json.dumps(envelope, sort_keys=True),
    )
    return ConstitutionState(
        group_scope=state.group_scope,
        active_json=state.active_json,
        predecessor_version=state.predecessor_version,
        activated_at=state.activated_at,
        last_pre_mortem=state.last_pre_mortem,
        pending=(pending,),
        seq=seq,
    )


def _activate(state: ConstitutionState, payload: dict[str, object], seq: int) -> ConstitutionState:
    envelope = _envelope(payload)
    _same_scope(state, envelope)
    now = str(payload["activated_at"])
    window_open(envelope, now)
    version = int(envelope["version"])
    _predecessor(state, payload.get("predecessor_version"))
    if state.active_json is None:
        if version != 1:
            raise ConstitutionError("the first activation is version 1", code="version")
        return _install(state, envelope, None, now, seq, pending=(), pre_mortem=None)
    if not state.pending or state.pending[0].version != version:
        raise ConstitutionError("activation requires the visible pending proposal", code="pending")
    item = state.pending[0]
    if item.envelope_json != json.dumps(envelope, sort_keys=True):
        raise ConstitutionError("activation does not match the pending proposal", code="mismatch")
    _lock_elapsed(item, now)
    if item.change_class == "lock_hours" and not lock_hours_are_ordered(envelope["document"]):
        raise ConstitutionError("tighten lock must be shorter than loosen lock", code="time_lock")
    previous = active_version(state)
    return _install(state, envelope, previous, now, seq, pending=(), pre_mortem=None)


def _emergency(state: ConstitutionState, payload: dict[str, object], seq: int) -> ConstitutionState:
    envelope = _envelope(payload)
    _same_scope(state, envelope)
    current = active_document(state)
    if current is None:
        raise ConstitutionError("emergency tightening needs an active constitution", code="version")
    pre_mortem = _text(payload.get("pre_mortem"), "emergency tightening needs a pre-mortem", "pre_mortem")
    _predecessor(state, payload.get("predecessor_version"))
    if classify(current, envelope["document"]) != "tighten":
        raise ConstitutionError("emergency loosening is prohibited", code="emergency_loosen")
    now = str(payload["activated_at"])
    window_open(envelope, now)
    previous = active_version(state)
    return _install(state, envelope, previous, now, seq, pending=(), pre_mortem=pre_mortem)


def _install(
    state: ConstitutionState,
    envelope: dict[str, object],
    predecessor: int | None,
    activated_at: str,
    seq: int,
    *,
    pending: tuple[Pending, ...],
    pre_mortem: str | None,
) -> ConstitutionState:
    return ConstitutionState(
        group_scope=state.group_scope,
        active_json=json.dumps(envelope, sort_keys=True),
        predecessor_version=predecessor,
        activated_at=activated_at,
        last_pre_mortem=pre_mortem,
        pending=pending,
        seq=seq,
    )


def _lock_hours(
    current: dict[str, object],
    proposed: dict[str, object],
    change_class: str,
) -> int | None:
    if change_class == "lock_hours":
        if not hours_are_placeholder(current):
            raise ConstitutionError("lock hours are no longer a placeholder", code="time_lock")
        if not lock_hours_are_ordered(proposed):
            raise ConstitutionError("tighten lock must be shorter than loosen lock", code="time_lock")
        return 0
    if hours_are_placeholder(current):
        return None
    if change_class == "tighten":
        return int(current["meta"]["tighten_lock_hours"])
    return int(current["meta"]["loosen_lock_hours"])


def _lock_elapsed(item: Pending, now: str) -> None:
    if item.lock_hours is None:
        raise ConstitutionError(
            "time-lock hours are still the owner placeholder",
            code="time_lock_unset",
        )
    eligible = add_hours(item.proposed_at, item.lock_hours)
    if now < eligible:
        raise ConstitutionError("time-lock has not finished", code="time_lock")


def _envelope(payload: dict[str, object]) -> dict[str, object]:
    envelope = payload.get("envelope")
    if not isinstance(envelope, dict):
        raise ConstitutionError("constitution envelope is missing", code="malformed")
    validate_envelope(envelope)
    return envelope


def _verify(envelope: dict[str, object], public_key: bytes, key_id: str, now: str) -> None:
    if not str(envelope.get("signature", "")).strip():
        raise ConstitutionError("constitution is unsigned", code="unsigned")
    validate_envelope(envelope)
    if envelope.get("key_id") != key_id:
        raise ConstitutionError("constitution key id is not pinned", code="key_id")
    if not signature_valid(envelope, public_key):
        raise ConstitutionError("constitution signature is invalid", code="signature")
    window_open(envelope, now)


def _same_scope(state: ConstitutionState, envelope: dict[str, object]) -> None:
    if envelope["group_id"] != state.group_scope:
        raise ConstitutionError("constitution group does not match the service scope", code="scope")


def _pending_row(item: Pending) -> dict[str, object]:
    if item.lock_hours is None:
        lock_state = "awaiting_owner_hours"
        eligible_at = None
    else:
        eligible_at = add_hours(item.proposed_at, item.lock_hours)
        lock_state = "eligible" if item.lock_hours == 0 else "locked"
    return {
        "version": item.version,
        "proposed_at": item.proposed_at,
        "reason": item.reason,
        "change_class": item.change_class,
        "paths": list(item.paths),
        "lock_state": lock_state,
        "eligible_at": eligible_at,
        "visible": True,
    }


def _advance(state: ConstitutionState, seq: int) -> ConstitutionState:
    return ConstitutionState(
        group_scope=state.group_scope,
        active_json=state.active_json,
        predecessor_version=state.predecessor_version,
        activated_at=state.activated_at,
        last_pre_mortem=state.last_pre_mortem,
        pending=state.pending,
        seq=seq,
    )


def _text(value: object, message: str, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConstitutionError(message, code=code)
    return value.strip()


def _predecessor(state: ConstitutionState, claimed: object) -> None:
    current = active_version(state)
    if claimed != current:
        raise ConstitutionError("predecessor does not match the active version", code="version")
