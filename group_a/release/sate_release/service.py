"""One active KERNEL-A artifact. Staging does not make it the running artifact."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sate_factlog.log import FactRecord

from sate_release.artifact import Pins, verify_authorization, verify_envelope
from sate_release.errors import ReleaseError
from sate_release.redteam import require_suite

_WRITER = "release"
_CONSUMED = frozenset({"deployment", "signature"})


@dataclass(frozen=True)
class Held:
    binary_sha256: str
    git_sha: str
    constitution_hash: str
    constitution_version: int
    suite_version: str
    suite_cases: tuple[str, ...]
    envelope: dict[str, object]


@dataclass(frozen=True)
class ReleaseState:
    group_scope: str
    anchor: Pins
    pins: Pins
    active: Held | None
    previous: Held | None
    staged: Held | None
    reprovision_required: bool
    rollback_started_at: str | None
    rollback_finished_at: str | None
    change_id: str | None = None
    change_reason: str | None = None
    safety_domains: tuple[str, ...] = ()
    seq: int = 0


def blank(pins: Pins) -> ReleaseState:
    identities = {pins.build_key_id, pins.deploy_key_id, pins.constitution_key_id}
    if len(identities) != 3:
        raise ReleaseError("build, deploy, and constitution keys are distinct", code="scope")
    pins.public_bytes("build")
    pins.public_bytes("deploy")
    return ReleaseState(
        group_scope="A",
        anchor=pins,
        pins=pins,
        active=None,
        previous=None,
        staged=None,
        reprovision_required=False,
        rollback_started_at=None,
        rollback_finished_at=None,
        seq=0,
    )


def view(state: ReleaseState) -> dict[str, object]:
    active = state.active
    started = state.rollback_started_at
    finished = state.rollback_finished_at
    elapsed = None if started is None or finished is None else _seconds(started, finished)
    return {
        "group_scope": state.group_scope,
        "active_binary_sha256": None if active is None else active.binary_sha256,
        "previous_binary_sha256": None if state.previous is None else state.previous.binary_sha256,
        "staged_binary_sha256": None if state.staged is None else state.staged.binary_sha256,
        "git_sha": None if active is None else active.git_sha,
        "constitution_version": None if active is None else active.constitution_version,
        "constitution_hash": None if active is None else active.constitution_hash,
        "build_key_id": state.pins.build_key_id,
        "deploy_key_id": state.pins.deploy_key_id,
        "revoked_key_ids": list(state.pins.revoked),
        "reprovision_required": state.reprovision_required,
        "required_action": "K3" if state.reprovision_required else None,
        "suite_version": None if active is None else active.suite_version,
        "suite_cases": [] if active is None else list(active.suite_cases),
        "change_id": state.change_id,
        "change_reason": state.change_reason,
        "safety_domains": list(state.safety_domains),
        "rollback_started_at": started,
        "rollback_finished_at": finished,
        "rollback_elapsed_seconds": elapsed,
    }


def project(state: ReleaseState, records: list[FactRecord]) -> ReleaseState:
    ordered = sorted(records, key=lambda record: record.seq)
    for record in ordered:
        state = fold(state, record)
    return state


def fold(state: ReleaseState, record: FactRecord) -> ReleaseState:
    if record.event_type not in _CONSUMED:
        return _advance(state, record.seq)
    if record.group_scope == "GLOBAL":
        raise ReleaseError("a kernel release cannot be pooled", code="pooled")
    if record.group_scope != state.group_scope:
        return _advance(state, record.seq)
    if record.writer_id != _WRITER:
        raise ReleaseError("release writer is required", code="writer")
    return apply_event(state, record.payload, record.seq)


def apply_event(state: ReleaseState, payload: dict[str, object], seq: int) -> ReleaseState:
    kind = str(payload.get("kind", ""))
    if state.reprovision_required and kind in {"stage", "activate", "rollback"}:
        raise ReleaseError("suspected compromise requires K3 and re-provision", code="reprovision")
    if kind == "stage":
        return _stage(state, payload, seq)
    if kind == "activate":
        return _activate(state, payload, seq)
    if kind == "rollback":
        return _rollback(state, payload, seq)
    if kind == "rotate":
        return _rotate(state, payload, seq)
    if kind == "revoke":
        return _revoke(state, payload, seq)
    raise ReleaseError("unknown release event", code="malformed")


def _stage(state: ReleaseState, payload: dict[str, object], seq: int) -> ReleaseState:
    suite_version, cases, digest = require_suite(payload)
    envelope = payload.get("envelope")
    if not isinstance(envelope, dict):
        raise ReleaseError("kernel artifact is malformed", code="malformed")
    manifest = verify_envelope(envelope, state.pins)
    if manifest["binary_sha256"] != digest:
        raise ReleaseError("red-team suite failed", code="redteam")
    staged = _held(manifest, suite_version, cases, envelope)
    return ReleaseState(
        group_scope=state.group_scope,
        anchor=state.anchor,
        pins=state.pins,
        active=state.active,
        previous=state.previous,
        staged=staged,
        reprovision_required=state.reprovision_required,
        rollback_started_at=state.rollback_started_at,
        rollback_finished_at=state.rollback_finished_at,
        change_id=state.change_id,
        change_reason=state.change_reason,
        safety_domains=state.safety_domains,
        seq=seq,
    )


def _activate(state: ReleaseState, payload: dict[str, object], seq: int) -> ReleaseState:
    if state.staged is None:
        raise ReleaseError("activation requires the staged artifact", code="pending")
    body = _authorized(state, payload, state.staged, "activate")
    return ReleaseState(
        group_scope=state.group_scope,
        anchor=state.anchor,
        pins=state.pins,
        active=state.staged,
        previous=state.active,
        staged=None,
        reprovision_required=False,
        rollback_started_at=state.rollback_started_at,
        rollback_finished_at=state.rollback_finished_at,
        change_id=_text(body, "change_id"),
        change_reason=_text(body, "reason"),
        safety_domains=_domains(body),
        seq=seq,
    )


def _rollback(state: ReleaseState, payload: dict[str, object], seq: int) -> ReleaseState:
    if state.previous is None or state.active is None:
        raise ReleaseError("rollback requires the previous artifact", code="rollback")
    _suite_version, _cases, digest = require_suite(payload)
    if digest != state.previous.binary_sha256:
        raise ReleaseError("red-team suite failed", code="redteam")
    body = _authorized(state, payload, state.previous, "rollback")
    started = str(payload.get("started_at", ""))
    finished = str(payload.get("finished_at", ""))
    if _seconds(started, finished) < 0:
        raise ReleaseError("rollback finished before it started", code="provenance")
    return ReleaseState(
        group_scope=state.group_scope,
        anchor=state.anchor,
        pins=state.pins,
        active=state.previous,
        previous=state.active,
        staged=None,
        reprovision_required=False,
        rollback_started_at=started,
        rollback_finished_at=finished,
        change_id=_text(body, "change_id"),
        change_reason=_text(body, "reason"),
        safety_domains=_domains(body),
        seq=seq,
    )


def _rotate(state: ReleaseState, payload: dict[str, object], seq: int) -> ReleaseState:
    old_key = str(payload.get("old_key_id", ""))
    new_key = str(payload.get("new_key_id", "")).strip()
    new_public = str(payload.get("new_public_key_hex", "")).strip()
    if old_key != state.pins.build_key_id:
        raise ReleaseError("rotation must replace the pinned build key", code="key_id")
    if not new_key or new_key in state.pins.revoked or new_key == state.pins.constitution_key_id:
        raise ReleaseError("rotated build key is not usable", code="revoked")
    if new_key == state.pins.deploy_key_id:
        raise ReleaseError("build, deploy, and constitution keys are distinct", code="scope")
    pins = Pins(
        build_key_id=new_key,
        build_public_hex=new_public,
        deploy_key_id=state.pins.deploy_key_id,
        deploy_public_hex=state.pins.deploy_public_hex,
        constitution_key_id=state.pins.constitution_key_id,
        constitution_version=state.pins.constitution_version,
        constitution_hash=state.pins.constitution_hash,
        revoked=state.pins.revoked + (old_key,),
    )
    pins.public_bytes("build")
    return _with_pins(state, pins, seq, reprovision_required=False)


def _revoke(state: ReleaseState, payload: dict[str, object], seq: int) -> ReleaseState:
    key_id = str(payload.get("key_id", ""))
    if payload.get("required_action") != "K3":
        raise ReleaseError("suspected compromise requires K3 and re-provision", code="reprovision")
    if key_id != state.pins.build_key_id:
        raise ReleaseError("revocation names the pinned build key", code="key_id")
    pins = Pins(
        build_key_id=state.pins.build_key_id,
        build_public_hex=state.pins.build_public_hex,
        deploy_key_id=state.pins.deploy_key_id,
        deploy_public_hex=state.pins.deploy_public_hex,
        constitution_key_id=state.pins.constitution_key_id,
        constitution_version=state.pins.constitution_version,
        constitution_hash=state.pins.constitution_hash,
        revoked=state.pins.revoked + (key_id,),
    )
    return _with_pins(state, pins, seq, reprovision_required=True)


def _authorized(state: ReleaseState, payload: dict[str, object], held: Held, action: str) -> dict[str, object]:
    envelope = payload.get("authorization")
    if not isinstance(envelope, dict):
        raise ReleaseError("deployment authorization is unsigned", code="unsigned")
    body = verify_authorization(envelope, state.pins, _held_fields(held))
    if body.get("action") != action:
        raise ReleaseError("authorization does not match the artifact", code="mismatch")
    return body


def _held(
    manifest: dict[str, object],
    suite_version: str,
    suite_cases: tuple[str, ...],
    envelope: dict[str, object],
) -> Held:
    return Held(
        binary_sha256=str(manifest["binary_sha256"]),
        git_sha=str(manifest["git_sha"]),
        constitution_hash=str(manifest["constitution_hash"]),
        constitution_version=int(manifest["constitution_version"]),
        suite_version=suite_version,
        suite_cases=suite_cases,
        envelope=envelope,
    )


def _held_fields(held: Held) -> dict[str, object]:
    return {
        "git_sha": held.git_sha,
        "constitution_hash": held.constitution_hash,
        "constitution_version": held.constitution_version,
        "binary_sha256": held.binary_sha256,
    }


def _with_pins(state: ReleaseState, pins: Pins, seq: int, *, reprovision_required: bool) -> ReleaseState:
    return ReleaseState(
        group_scope=state.group_scope,
        anchor=state.anchor,
        pins=pins,
        active=state.active,
        previous=state.previous,
        staged=None,
        reprovision_required=reprovision_required,
        rollback_started_at=state.rollback_started_at,
        rollback_finished_at=state.rollback_finished_at,
        change_id=state.change_id,
        change_reason=state.change_reason,
        safety_domains=state.safety_domains,
        seq=seq,
    )


def _advance(state: ReleaseState, seq: int) -> ReleaseState:
    return ReleaseState(
        group_scope=state.group_scope,
        anchor=state.anchor,
        pins=state.pins,
        active=state.active,
        previous=state.previous,
        staged=state.staged,
        reprovision_required=state.reprovision_required,
        rollback_started_at=state.rollback_started_at,
        rollback_finished_at=state.rollback_finished_at,
        change_id=state.change_id,
        change_reason=state.change_reason,
        safety_domains=state.safety_domains,
        seq=seq,
    )


def _text(body: dict[str, object], field: str) -> str:
    return str(body[field]).strip()


def _domains(body: dict[str, object]) -> tuple[str, ...]:
    domains = body["safety_domains"]
    return tuple(str(item).strip() for item in domains)


def _seconds(started: str, finished: str) -> int:
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    try:
        left = datetime.strptime(started, fmt).replace(tzinfo=UTC)
        right = datetime.strptime(finished, fmt).replace(tzinfo=UTC)
    except ValueError as exc:
        raise ReleaseError("rollback timestamps are required", code="provenance") from exc
    return int((right - left).total_seconds())
