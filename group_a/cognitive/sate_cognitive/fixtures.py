"""Signed AdvisorySignal fixtures for SIM shadow (no network)."""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from sate_cognitive.signing import canonical_payload


def generate_keypair() -> tuple[bytes, bytes]:
    private = Ed25519PrivateKey.generate()
    return private.private_bytes_raw(), private.public_key().public_bytes_raw()


def signed_signal(private_key: bytes, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "signal_id": "sig-test",
        "cycle_id": "cycle-1",
        "instrument": "EURUSD",
        "horizon": "1h",
        "state": "ACTIVE",
        "q": 0.15,
        "c": 0.4,
        "evidence_refs": ["fact://ok"],
        "valid_from": "2026-10-23T00:00:00Z",
        "valid_until": "2026-10-24T00:00:00Z",
        "model_id": "test",
        "prompt_hash": "ph-1",
        "calibration_version": "shadow-v1",
        "abstain_reason": None,
    }
    body.update(overrides)
    signature = Ed25519PrivateKey.from_private_bytes(private_key).sign(canonical_payload(body))
    body["signature"] = base64.b64encode(signature).decode()
    return body
