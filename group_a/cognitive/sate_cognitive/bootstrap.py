"""Compose smoke: valid signed signal ingests with trading multiplier 0."""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from sate_cognitive.ingest import ingest_signal
from sate_cognitive.signing import canonical_payload


def _sign(private_key: bytes, body: dict[str, object]) -> dict[str, object]:
    signed = dict(body)
    signature = Ed25519PrivateKey.from_private_bytes(private_key).sign(canonical_payload(body))
    signed["signature"] = base64.b64encode(signature).decode()
    return signed


def main() -> None:
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes_raw()
    secret = private.private_bytes_raw()
    body = {
        "signal_id": "sig-1",
        "cycle_id": "c-1",
        "instrument": "EURUSD",
        "horizon": "1h",
        "state": "ACTIVE",
        "q": 0.2,
        "c": 0.5,
        "evidence_refs": ["fact://corr-1"],
        "valid_from": "2026-10-23T00:00:00Z",
        "valid_until": "2026-10-24T00:00:00Z",
        "model_id": "shadow-model",
        "prompt_hash": "abc123",
        "calibration_version": "shadow-v1",
        "abstain_reason": None,
    }
    signal = _sign(secret, body)
    result = ingest_signal(signal, now="2026-10-23T12:00:00Z", public_key=public, account_mode="LIVE")
    if not result.ok or result.trading_view is not None:
        raise SystemExit("expected shadow ok with zero trading view")
    print("cognitive ok")


if __name__ == "__main__":
    main()
