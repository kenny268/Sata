"""Ed25519 verify for AdvisorySignal (**§11**)."""

from __future__ import annotations

import base64
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def canonical_payload(signal: dict[str, object]) -> bytes:
    body = {key: value for key, value in signal.items() if key != "signature"}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def verify_signature(signal: dict[str, object], *, public_key: bytes) -> bool:
    signature_b64 = str(signal.get("signature", ""))
    try:
        signature = base64.b64decode(signature_b64, validate=True)
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, canonical_payload(signal))
    except (InvalidSignature, ValueError):
        return False
    return True
