"""Record release events on the fact log. Activation is not a file copy."""

from __future__ import annotations

from sate_factlog.log import FactLog

from sate_release.artifact import (
    Pins,
    verify_authorization,
    verify_binary,
    verify_envelope,
)
from sate_release.errors import ReleaseError
from sate_release.redteam import run_suite
from sate_release.service import ReleaseState, apply_event, blank, project

_WRITER = "release"
_POLLED = ("A", "B", "GLOBAL")


def submit_stage(
    log: FactLog,
    state: ReleaseState,
    envelope: dict[str, object],
    binary: bytes,
    *,
    now: str,
    **identity: str,
) -> ReleaseState:
    manifest = verify_envelope(envelope, state.pins)
    verify_binary(manifest, binary)
    suite = run_suite(envelope, binary, state.pins)
    occurred_at = identity.pop("occurred_at", now)
    return _commit(
        log,
        state,
        {"kind": "stage", "envelope": envelope, **suite},
        occurred_at=occurred_at,
        **identity,
    )


def submit_activate(
    log: FactLog,
    state: ReleaseState,
    authorization: dict[str, object],
    *,
    now: str,
    **identity: str,
) -> ReleaseState:
    if state.staged is None:
        raise ReleaseError("activation requires the staged artifact", code="pending")
    verify_authorization(authorization, state.pins, _fields(state.staged))
    occurred_at = identity.pop("occurred_at", now)
    body = {"kind": "activate", "authorization": authorization}
    return _commit(log, state, body, occurred_at=occurred_at, **identity)


def submit_rollback(
    log: FactLog,
    state: ReleaseState,
    authorization: dict[str, object],
    binary: bytes,
    *,
    now: str,
    started_at: str,
    **identity: str,
) -> ReleaseState:
    if state.previous is None:
        raise ReleaseError("rollback requires the previous artifact", code="rollback")
    manifest = verify_envelope(state.previous.envelope, state.pins)
    verify_binary(manifest, binary)
    suite = run_suite(state.previous.envelope, binary, state.pins)
    verify_authorization(authorization, state.pins, _fields(state.previous))
    occurred_at = identity.pop("occurred_at", now)
    body = {
        "kind": "rollback",
        "authorization": authorization,
        "started_at": started_at,
        "finished_at": now,
        **suite,
    }
    return _commit(log, state, body, occurred_at=occurred_at, **identity)


def submit_rotate(
    log: FactLog,
    state: ReleaseState,
    *,
    new_key_id: str,
    new_public_key_hex: str,
    now: str,
    **identity: str,
) -> ReleaseState:
    occurred_at = identity.pop("occurred_at", now)
    body = {
        "kind": "rotate",
        "old_key_id": state.pins.build_key_id,
        "new_key_id": new_key_id,
        "new_public_key_hex": new_public_key_hex,
    }
    return _commit(log, state, body, occurred_at=occurred_at, **identity)


def submit_revoke(
    log: FactLog,
    state: ReleaseState,
    *,
    now: str,
    **identity: str,
) -> ReleaseState:
    occurred_at = identity.pop("occurred_at", now)
    body = {"kind": "revoke", "key_id": state.pins.build_key_id, "required_action": "K3"}
    return _commit(log, state, body, occurred_at=occurred_at, **identity)


def replay(log: FactLog, pins: Pins) -> ReleaseState:
    records = []
    for group in _POLLED:
        records.extend(log.poll(after_seq=0, group_scope=group, reader_id=_WRITER))
    return project(blank(pins), records)


def _fields(held: object) -> dict[str, object]:
    return {
        "git_sha": held.git_sha,
        "constitution_hash": held.constitution_hash,
        "constitution_version": held.constitution_version,
        "binary_sha256": held.binary_sha256,
    }


def _commit(
    log: FactLog,
    state: ReleaseState,
    payload: dict[str, object],
    *,
    event_id: str,
    occurred_at: str,
    recorded_at: str,
    correlation_id: str,
) -> ReleaseState:
    for group in _POLLED:
        for record in log.poll(after_seq=0, group_scope=group, reader_id=_WRITER):
            if record.event_id == event_id:
                return replay(log, state.anchor)
    apply_event(state, payload, state.seq + 1)
    event_type = "signature" if payload["kind"] in {"rotate", "revoke"} else "deployment"
    log.append(
        event_id=event_id,
        event_type=event_type,
        group_scope=state.group_scope,
        occurred_at=occurred_at,
        recorded_at=recorded_at,
        correlation_id=correlation_id,
        writer_id=_WRITER,
        payload=payload,
    )
    return replay(log, state.anchor)
