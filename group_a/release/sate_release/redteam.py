"""Frozen Phase 8 red-team cases. A missing result fails closed."""

from __future__ import annotations

from dataclasses import replace

from sate_release.artifact import Pins, verify_binary, verify_envelope
from sate_release.errors import ReleaseError

SUITE_VERSION = "phase-8"
CASES = ("wrong_signature", "downgraded_constitution", "tampered_binary")


def run_suite(envelope: dict[str, object], binary: bytes, pins: Pins) -> dict[str, object]:
    manifest = verify_envelope(envelope, pins)
    verify_binary(manifest, binary)
    _expect(_wrong_signature(envelope), pins, binary, "signature")
    higher = replace(pins, constitution_version=pins.constitution_version + 1)
    _expect(envelope, higher, binary, "downgrade")
    try:
        verify_binary(manifest, binary + b"\x00")
    except ReleaseError as exc:
        if exc.code != "tamper":
            raise ReleaseError("red-team suite failed", code="redteam") from exc
    else:
        raise ReleaseError("red-team suite failed", code="redteam")
    digest = str(manifest["binary_sha256"])
    return {
        "suite_version": SUITE_VERSION,
        "suite_results": [
            {"case": case, "passed": True, "binary_sha256": digest} for case in CASES
        ],
    }


def require_suite(payload: dict[str, object]) -> tuple[str, tuple[str, ...], str]:
    results = payload.get("suite_results")
    if payload.get("suite_version") != SUITE_VERSION or not isinstance(results, list):
        raise ReleaseError("red-team suite is missing", code="redteam_missing")
    cases: list[str] = []
    digest: str | None = None
    for row in results:
        if not isinstance(row, dict) or row.get("passed") is not True:
            raise ReleaseError("red-team suite failed", code="redteam")
        binary_sha = row.get("binary_sha256")
        if not isinstance(binary_sha, str) or (digest is not None and binary_sha != digest):
            raise ReleaseError("red-team suite failed", code="redteam")
        case = row.get("case")
        if not isinstance(case, str):
            raise ReleaseError("red-team suite is missing", code="redteam_missing")
        digest = binary_sha
        cases.append(case)
    if digest is None or tuple(cases) != CASES:
        raise ReleaseError("red-team suite is missing", code="redteam_missing")
    return SUITE_VERSION, CASES, digest


def _wrong_signature(envelope: dict[str, object]) -> dict[str, object]:
    signature = str(envelope["signature"])
    last = "b" if signature[-1] == "a" else "a"
    changed = dict(envelope)
    changed["signature"] = signature[:-1] + last
    return changed


def _expect(envelope: dict[str, object], pins: Pins, binary: bytes, code: str) -> None:
    try:
        manifest = verify_envelope(envelope, pins)
        verify_binary(manifest, binary)
    except ReleaseError as exc:
        if exc.code != code:
            raise ReleaseError("red-team suite failed", code="redteam") from exc
        return
    raise ReleaseError("red-team suite failed", code="redteam")
