"""Signed deploy, red-team gate, rotation, and rollback for KERNEL-A."""

from __future__ import annotations

import json
import os
import sqlite3
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sate_factlog.log import FactLog

from sate_release.artifact import (
    Pins,
    seal_authorization,
    seal_manifest,
    verify_envelope,
)
from sate_release.bootstrap import main, matches_replay, pins_from
from sate_release.errors import ReleaseError
from sate_release.service import blank, view
from sate_release.signing import generate_keypair
from sate_release.sourced import (
    replay,
    submit_activate,
    submit_revoke,
    submit_rollback,
    submit_rotate,
    submit_stage,
)
import sate_release.sourced as sourced

_ROOT = Path(__file__).resolve().parents[1]
_NOW = "2026-10-22T21:00:00Z"
_GIT = "a" * 40
_HASH = "b" * 64
_FIFTEEN_MINUTES = 15 * 60


class _Ids:
    def __init__(self) -> None:
        self._n = 0

    def __call__(self, when: str = _NOW) -> dict[str, str]:
        self._n += 1
        return {
            "event_id": f"r-{self._n}",
            "recorded_at": when,
            "correlation_id": "release-a",
            "occurred_at": when,
        }


def _log() -> FactLog:
    return FactLog(sqlite3.connect(":memory:"), writers=frozenset({"release"}))


def _pins(build_public: bytes, deploy_public: bytes, **overrides: object) -> Pins:
    values: dict[str, object] = {
        "build_key_id": "build-key-1",
        "build_public_hex": build_public.hex(),
        "deploy_key_id": "deploy-key-1",
        "deploy_public_hex": deploy_public.hex(),
        "constitution_key_id": "owner-key-1",
        "constitution_version": 1,
        "constitution_hash": _HASH,
    }
    values.update(overrides)
    return Pins(**values)  # type: ignore[arg-type]


def _manifest(private: bytes, binary: bytes, *, key_id: str = "build-key-1", version: int = 1) -> dict:
    return seal_manifest(
        private_key=private,
        key_id=key_id,
        constitution_key_id="owner-key-1",
        git_sha=_GIT,
        constitution_hash=_HASH,
        constitution_version=version,
        binary=binary,
        built_at=_NOW,
    )


def _authorize(
    manifest: dict,
    private: bytes,
    *,
    action: str = "activate",
    when: str = _NOW,
    reason: str = "ship the signed kernel",
) -> dict:
    return seal_authorization(
        manifest["manifest"],
        action=action,
        private_key=private,
        key_id="deploy-key-1",
        build_key_id="build-key-1",
        constitution_key_id="owner-key-1",
        authorized_at=when,
        change_id="chg-1",
        reason=reason,
        safety_domains=["kernel-artifact"],
    )


class ReleaseTests(unittest.TestCase):
    def test_constitution_key_cannot_sign_the_kernel(self) -> None:
        private, _public = generate_keypair()
        with self.assertRaises(ReleaseError) as caught:
            seal_manifest(
                private_key=private,
                key_id="owner-key-1",
                constitution_key_id="owner-key-1",
                git_sha=_GIT,
                constitution_hash=_HASH,
                constitution_version=1,
                binary=b"kernel-a",
                built_at=_NOW,
            )
        self.assertEqual(caught.exception.code, "scope")

    def test_unsigned_tampered_and_downgraded_artifacts_do_not_activate(self) -> None:
        build_secret, build_public = generate_keypair()
        _deploy_secret, deploy_public = generate_keypair()
        binary = b"kernel-a"
        pins = _pins(build_public, deploy_public)
        state = blank(pins)
        log = _log()
        ids = _Ids()
        signed = _manifest(build_secret, binary)
        unsigned = dict(signed)
        unsigned["signature"] = ""
        with self.assertRaises(ReleaseError) as caught:
            submit_stage(log, state, unsigned, binary, now=_NOW, **ids())
        self.assertEqual(caught.exception.code, "unsigned")
        flipped = dict(signed)
        last = "b" if signed["signature"][-1] == "a" else "a"
        flipped["signature"] = signed["signature"][:-1] + last
        with self.assertRaises(ReleaseError) as caught:
            submit_stage(log, state, flipped, binary, now=_NOW, **ids())
        self.assertEqual(caught.exception.code, "signature")
        with self.assertRaises(ReleaseError) as caught:
            submit_stage(log, state, signed, binary + b"\x00", now=_NOW, **ids())
        self.assertEqual(caught.exception.code, "tamper")
        higher = _pins(build_public, deploy_public, constitution_version=2)
        with self.assertRaises(ReleaseError) as caught:
            verify_envelope(signed, higher)
        self.assertEqual(caught.exception.code, "downgrade")
        self.assertIsNone(view(replay(log, pins))["active_binary_sha256"])

    def test_only_a_deploy_authorization_activates_the_staged_artifact(self) -> None:
        build_secret, build_public = generate_keypair()
        deploy_secret, deploy_public = generate_keypair()
        binary = b"kernel-a"
        pins = _pins(build_public, deploy_public)
        log = _log()
        ids = _Ids()
        signed = _manifest(build_secret, binary)
        state = submit_stage(log, blank(pins), signed, binary, now=_NOW, **ids())
        self.assertIsNone(view(state)["active_binary_sha256"])
        self.assertIsNotNone(view(state)["staged_binary_sha256"])
        with self.assertRaises(ReleaseError) as caught:
            seal_authorization(
                signed["manifest"],
                action="activate",
                private_key=build_secret,
                key_id="build-key-1",
                build_key_id="build-key-1",
                constitution_key_id="owner-key-1",
                authorized_at=_NOW,
                change_id="chg-1",
                reason="ship the signed kernel",
                safety_domains=["kernel-artifact"],
            )
        self.assertEqual(caught.exception.code, "scope")
        state = submit_activate(log, state, _authorize(signed, deploy_secret), now=_NOW, **ids())
        self.assertEqual(view(state)["active_binary_sha256"], signed["manifest"]["binary_sha256"])
        self.assertIsNone(view(state)["staged_binary_sha256"])
        self.assertEqual(view(state)["suite_version"], "phase-8")
        self.assertEqual(
            view(state)["suite_cases"],
            ["wrong_signature", "downgraded_constitution", "tampered_binary"],
        )
        self.assertEqual(view(state)["change_id"], "chg-1")
        self.assertEqual(view(state)["change_reason"], "ship the signed kernel")
        self.assertEqual(view(state)["safety_domains"], ["kernel-artifact"])
        with self.assertRaises(ReleaseError) as caught:
            _authorize(signed, deploy_secret, reason="  ")
        self.assertEqual(caught.exception.code, "reason")
        names = {name for name in dir(sourced) if name.startswith("submit_")}
        self.assertEqual(
            names,
            {"submit_activate", "submit_revoke", "submit_rollback", "submit_rotate", "submit_stage"},
        )
        self.assertFalse(hasattr(sourced, "swap_binary"))

    def test_rollback_finishes_within_fifteen_minutes(self) -> None:
        build_secret, build_public = generate_keypair()
        deploy_secret, deploy_public = generate_keypair()
        pins = _pins(build_public, deploy_public)
        log = _log()
        ids = _Ids()
        first_bytes = b"kernel-a-v1"
        second_bytes = b"kernel-a-v2"
        first = _manifest(build_secret, first_bytes)
        second = _manifest(build_secret, second_bytes)
        state = blank(pins)
        state = submit_stage(log, state, first, first_bytes, now=_NOW, **ids())
        state = submit_activate(log, state, _authorize(first, deploy_secret), now=_NOW, **ids())
        later = "2026-10-22T21:10:00Z"
        state = submit_stage(log, state, second, second_bytes, now=later, **ids(later))
        state = submit_activate(
            log, state, _authorize(second, deploy_secret, when=later), now=later, **ids(later)
        )
        started = time.monotonic()
        finished = "2026-10-22T21:14:00Z"
        state = submit_rollback(
            log,
            state,
            _authorize(first, deploy_secret, action="rollback", when=later),
            first_bytes,
            now=finished,
            started_at=later,
            **ids(finished),
        )
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, _FIFTEEN_MINUTES)
        self.assertEqual(view(state)["active_binary_sha256"], first["manifest"]["binary_sha256"])
        self.assertLessEqual(view(state)["rollback_elapsed_seconds"], _FIFTEEN_MINUTES)
        self.assertEqual(view(replay(log, pins))["active_binary_sha256"], first["manifest"]["binary_sha256"])

    def test_rotation_drill_revokes_the_old_build_key(self) -> None:
        build_secret, build_public = generate_keypair()
        deploy_secret, deploy_public = generate_keypair()
        next_secret, next_public = generate_keypair()
        pins = _pins(build_public, deploy_public)
        log = _log()
        ids = _Ids()
        binary = b"kernel-a"
        signed = _manifest(build_secret, binary)
        state = submit_stage(log, blank(pins), signed, binary, now=_NOW, **ids())
        state = submit_activate(log, state, _authorize(signed, deploy_secret), now=_NOW, **ids())
        state = submit_rotate(
            log,
            state,
            new_key_id="build-key-2",
            new_public_key_hex=next_public.hex(),
            now=_NOW,
            **ids(),
        )
        self.assertEqual(view(state)["build_key_id"], "build-key-2")
        self.assertIn("build-key-1", view(state)["revoked_key_ids"])
        with self.assertRaises(ReleaseError) as caught:
            submit_stage(log, state, signed, binary, now=_NOW, **ids())
        self.assertEqual(caught.exception.code, "revoked")
        replacement = _manifest(next_secret, b"kernel-a-rotated", key_id="build-key-2")
        state = submit_stage(log, state, replacement, b"kernel-a-rotated", now=_NOW, **ids())
        self.assertEqual(view(state)["staged_binary_sha256"], replacement["manifest"]["binary_sha256"])

    def test_compromise_requires_k3_reprovision(self) -> None:
        build_secret, build_public = generate_keypair()
        deploy_secret, deploy_public = generate_keypair()
        next_secret, next_public = generate_keypair()
        pins = _pins(build_public, deploy_public)
        log = _log()
        ids = _Ids()
        binary = b"kernel-a"
        signed = _manifest(build_secret, binary)
        state = submit_stage(log, blank(pins), signed, binary, now=_NOW, **ids())
        state = submit_activate(log, state, _authorize(signed, deploy_secret), now=_NOW, **ids())
        active = view(state)["active_binary_sha256"]
        state = submit_revoke(log, state, now=_NOW, **ids())
        self.assertTrue(view(state)["reprovision_required"])
        self.assertEqual(view(state)["required_action"], "K3")
        with self.assertRaises(ReleaseError) as caught:
            submit_stage(log, state, signed, binary, now=_NOW, **ids())
        self.assertEqual(caught.exception.code, "revoked")
        self.assertEqual(view(replay(log, pins))["active_binary_sha256"], active)
        state = submit_rotate(
            log,
            state,
            new_key_id="build-key-2",
            new_public_key_hex=next_public.hex(),
            now=_NOW,
            **ids(),
        )
        self.assertFalse(view(state)["reprovision_required"])
        replacement = _manifest(next_secret, b"kernel-a-new", key_id="build-key-2")
        state = submit_stage(log, state, replacement, b"kernel-a-new", now=_NOW, **ids())
        self.assertIsNotNone(view(state)["staged_binary_sha256"])

    def test_a_fact_log_stage_without_the_suite_does_not_replay(self) -> None:
        _build_secret, build_public = generate_keypair()
        _deploy_secret, deploy_public = generate_keypair()
        pins = _pins(build_public, deploy_public)
        log = _log()
        log.append(
            event_id="forged",
            event_type="deployment",
            group_scope="A",
            occurred_at=_NOW,
            recorded_at=_NOW,
            correlation_id="release-a",
            writer_id="release",
            payload={"kind": "stage", "envelope": {}},
        )
        with self.assertRaises(ReleaseError) as caught:
            replay(log, pins)
        self.assertEqual(caught.exception.code, "redteam_missing")
        partial_log = _log()
        partial_log.append(
            event_id="partial",
            event_type="deployment",
            group_scope="A",
            occurred_at=_NOW,
            recorded_at=_NOW,
            correlation_id="release-a",
            writer_id="release",
            payload={"kind": "stage", "suite_version": "phase-8", "suite_results": [], "envelope": {}},
        )
        with self.assertRaises(ReleaseError) as partial:
            replay(partial_log, pins)
        self.assertEqual(partial.exception.code, "redteam_missing")

    def test_release_package_does_not_touch_credentials(self) -> None:
        for path in (_ROOT / "sate_release").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("CredentialVault", text, str(path))
            self.assertNotIn("sate_a_credentials", text, str(path))

    def test_bootstrap_records_the_signed_stub(self) -> None:
        pin = json.loads((_ROOT / "config" / "staging.json").read_text(encoding="utf-8"))
        self.assertNotIn("private", json.dumps(pin))
        pins = pins_from(pin)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            fact = root / "fact.db"
            projection = root / "release.db"
            FactLog(sqlite3.connect(fact), writers=frozenset({"release"}))
            os.environ["SATE_FACTLOG_DB"] = str(fact)
            os.environ["SATE_RELEASE_DB"] = str(projection)
            main()
            opened = FactLog(sqlite3.connect(fact), writers=frozenset({"release"}))
            self.assertTrue(matches_replay(projection, opened, pins))
            stored = json.loads(sqlite3.connect(projection).execute("SELECT payload_json FROM projection").fetchone()[0])
            self.assertEqual(stored["constitution_version"], 1)
            self.assertFalse(stored["reprovision_required"])
            self.assertEqual(stored["suite_version"], "phase-8")
            self.assertEqual(stored["change_id"], "release-a-001")
            self.assertEqual(len(stored["suite_cases"]), 3)


if __name__ == "__main__":
    unittest.main()
