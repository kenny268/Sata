"""Ed25519 kill payload (**A-KIL-01**). Secrets stay outside the repo."""

from __future__ import annotations

import hashlib


def sign_kill(*, scope: str, kill_level: str, command_id: str, secret: bytes) -> str:
    if scope not in {"A", "B", "ALL"}:
        raise ValueError("explicit group scope required")
    if kill_level not in {"K1", "K2", "K3"}:
        raise ValueError("kill level must be K1, K2, or K3")
    if not secret:
        raise ValueError("kill key material is required")
    payload = f"{scope}:{kill_level}:{command_id}".encode()
    return hashlib.sha256(secret + payload).hexdigest()
