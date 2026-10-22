"""Signed KERNEL-A manifest and the separate deployment authorization."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import jsonschema

from sate_release.errors import ReleaseError
from sate_release.signing import canonical_bytes, sha256_hex, sign, verify

_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Pins:
    build_key_id: str
    build_public_hex: str
    deploy_key_id: str
    deploy_public_hex: str
    constitution_key_id: str
    constitution_version: int
    constitution_hash: str
    revoked: tuple[str, ...] = ()

    def public_bytes(self, role: str) -> bytes:
        hex_key = self.build_public_hex if role == "build" else self.deploy_public_hex
        try:
            raw = bytes.fromhex(hex_key)
        except ValueError as exc:
            raise ReleaseError("pinned verify key is malformed", code="key_id") from exc
        if len(raw) != 32:
            raise ReleaseError("pinned verify key is malformed", code="key_id")
        return raw


def schema_path() -> Path:
    override = os.environ.get("SATE_RELEASE_SCHEMA", "")
    if override:
        return Path(override)
    return _ROOT / "shared" / "schemas" / "kernel-release.schema.json"


def seal_manifest(
    *,
    private_key: bytes,
    key_id: str,
    constitution_key_id: str,
    git_sha: str,
    constitution_hash: str,
    constitution_version: int,
    binary: bytes,
    built_at: str,
) -> dict[str, object]:
    if key_id == constitution_key_id:
        raise ReleaseError("constitution key cannot sign the kernel artifact", code="scope")
    manifest = {
        "artifact_id": "kernel-a",
        "group_id": "A",
        "git_sha": git_sha,
        "constitution_hash": constitution_hash,
        "constitution_version": constitution_version,
        "binary_sha256": sha256_hex(binary),
        "built_at": built_at,
    }
    return _seal(manifest, "manifest", private_key=private_key, key_id=key_id)


def seal_authorization(
    manifest: dict[str, object],
    *,
    action: str,
    private_key: bytes,
    key_id: str,
    build_key_id: str,
    constitution_key_id: str,
    authorized_at: str,
    change_id: str,
    reason: str,
    safety_domains: list[str],
) -> dict[str, object]:
    if key_id in {build_key_id, constitution_key_id}:
        raise ReleaseError("deploy authorization uses the deploy key", code="scope")
    body = {
        "action": action,
        "artifact_id": manifest["artifact_id"],
        "group_id": manifest["group_id"],
        "git_sha": manifest["git_sha"],
        "constitution_hash": manifest["constitution_hash"],
        "constitution_version": manifest["constitution_version"],
        "binary_sha256": manifest["binary_sha256"],
        "authorized_at": authorized_at,
        "change_id": change_id,
        "reason": reason,
        "safety_domains": safety_domains,
    }
    _change_record(body)
    return _seal(body, "authorization", private_key=private_key, key_id=key_id)


def verify_envelope(envelope: dict[str, object], pins: Pins) -> dict[str, object]:
    _present_signature(envelope)
    _validate(envelope, "manifest_envelope")
    _build_scope(envelope, pins)
    manifest = _signed_body(envelope, "manifest", pins.public_bytes("build"))
    _constitution_pin(manifest, pins)
    return manifest


def verify_binary(manifest: dict[str, object], binary: bytes) -> None:
    if sha256_hex(binary) != manifest["binary_sha256"]:
        raise ReleaseError("kernel binary does not match the signed artifact", code="tamper")


def verify_authorization(
    envelope: dict[str, object],
    pins: Pins,
    held: dict[str, object],
) -> dict[str, object]:
    _present_signature(envelope)
    _validate(envelope, "authorization")
    if str(envelope.get("key_id")) != pins.deploy_key_id:
        raise ReleaseError("deploy key id is not pinned", code="key_id")
    if str(envelope.get("key_id")) in {pins.build_key_id, pins.constitution_key_id}:
        raise ReleaseError("build and constitution keys cannot authorize a deploy", code="scope")
    if pins.deploy_key_id in pins.revoked:
        raise ReleaseError("deploy key is revoked", code="revoked")
    body = _signed_body(envelope, "authorization", pins.public_bytes("deploy"))
    for field in ("git_sha", "constitution_hash", "constitution_version", "binary_sha256"):
        if body.get(field) != held.get(field):
            raise ReleaseError("authorization does not match the artifact", code="mismatch")
    _change_record(body)
    return body


def _seal(document: dict[str, object], field: str, *, private_key: bytes, key_id: str) -> dict[str, object]:
    canonical = canonical_bytes(document).decode()
    envelope = {
        "key_id": key_id,
        "payload_hash": sha256_hex(canonical.encode()),
        "signature": sign(private_key, canonical.encode()).hex(),
        "canonical": canonical,
        field: document,
    }
    definition = "manifest_envelope" if field == "manifest" else "authorization"
    _validate(envelope, definition)
    return envelope


def _change_record(body: dict[str, object]) -> None:
    if not str(body.get("change_id", "")).strip():
        raise ReleaseError("a deploy needs a change id", code="change")
    if not str(body.get("reason", "")).strip():
        raise ReleaseError("a deploy needs a change reason", code="reason")
    domains = body.get("safety_domains")
    if not isinstance(domains, list) or not domains:
        raise ReleaseError("a deploy needs its safety domains", code="change")
    if not all(isinstance(item, str) and item.strip() for item in domains):
        raise ReleaseError("a deploy needs its safety domains", code="change")


def _present_signature(envelope: dict[str, object]) -> None:
    signature = envelope.get("signature")
    if not isinstance(signature, str) or not signature.strip():
        raise ReleaseError("kernel artifact is unsigned", code="unsigned")


def _validate(instance: dict[str, object], definition: str) -> None:
    root = json.loads(schema_path().read_text(encoding="utf-8"))
    schema = {"$ref": f"#/$defs/{definition}", "$defs": root["$defs"]}
    try:
        jsonschema.validate(instance, schema)
    except jsonschema.ValidationError as exc:
        raise ReleaseError("kernel artifact is malformed", code="malformed") from exc


def _signed_body(envelope: dict[str, object], field: str, public_key: bytes) -> dict[str, object]:
    canonical = envelope.get("canonical")
    if not isinstance(canonical, str):
        raise ReleaseError("kernel artifact is malformed", code="malformed")
    if sha256_hex(canonical.encode()) != envelope.get("payload_hash"):
        raise ReleaseError("kernel artifact signature is invalid", code="signature")
    try:
        raw = bytes.fromhex(str(envelope.get("signature")))
    except ValueError as exc:
        raise ReleaseError("kernel artifact signature is invalid", code="signature") from exc
    if not verify(public_key, canonical.encode(), raw):
        raise ReleaseError("kernel artifact signature is invalid", code="signature")
    parsed = json.loads(canonical)
    if canonical_bytes(parsed).decode() != canonical or parsed != envelope.get(field):
        raise ReleaseError("kernel artifact signature is invalid", code="signature")
    return parsed


def _build_scope(envelope: dict[str, object], pins: Pins) -> None:
    key_id = str(envelope.get("key_id"))
    if key_id == pins.constitution_key_id:
        raise ReleaseError("constitution key cannot sign the kernel artifact", code="scope")
    if key_id == pins.deploy_key_id:
        raise ReleaseError("deploy key cannot sign the kernel artifact", code="scope")
    if key_id in pins.revoked:
        raise ReleaseError("build key is revoked", code="revoked")
    if key_id != pins.build_key_id:
        raise ReleaseError("build key id is not pinned", code="key_id")


def _constitution_pin(manifest: dict[str, object], pins: Pins) -> None:
    version = int(manifest["constitution_version"])
    if version < pins.constitution_version:
        raise ReleaseError("constitution version is downgraded", code="downgrade")
    if version != pins.constitution_version:
        raise ReleaseError("constitution version is not pinned", code="constitution_version")
    if manifest["constitution_hash"] != pins.constitution_hash:
        raise ReleaseError("constitution hash does not match the pin", code="constitution_hash")
