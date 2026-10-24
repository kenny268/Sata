"""Signed expiring confirm buttons (**TG-PO-05**, SEC-03)."""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class ConfirmToken:
    action: str
    scope: str
    expires_at: int


class ConfirmError(ValueError):
    pass


def sign_confirm(*, action: str, scope: str, ttl_sec: int, secret: bytes, now: int | None = None) -> str:
    moment = int(time.time()) if now is None else now
    expires = moment + ttl_sec
    body = f"{action}|{scope}|{expires}"
    digest = hmac.new(secret, body.encode(), hashlib.sha256).hexdigest()
    return f"{body}|{digest}"


def verify_confirm(token: str, *, secret: bytes, now: int | None = None) -> ConfirmToken:
    parts = token.split("|")
    if len(parts) != 4:
        raise ConfirmError("confirm token malformed")
    action, scope, expires_text, digest = parts
    body = f"{action}|{scope}|{expires_text}"
    expected = hmac.new(secret, body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(digest, expected):
        raise ConfirmError("confirm signature invalid")
    expires_at = int(expires_text)
    moment = int(time.time()) if now is None else now
    if moment > expires_at:
        raise ConfirmError("confirm token expired")
    return ConfirmToken(action=action, scope=scope, expires_at=expires_at)


def confirm_label(action: str, scope: str) -> str:
    return f"Confirm {action} {scope}"
