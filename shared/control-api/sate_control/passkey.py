"""WebAuthn passkey gate for risk-increasing actions (**A-PR-05**)."""

from __future__ import annotations

import base64
import binascii
import json
import re

_MIN_ASSERTION_LEN = 32
_BASE64URL = re.compile(r"^[A-Za-z0-9_-]+={0,2}$")


class PasskeyRequired(ValueError):
    def __init__(self, action: str) -> None:
        super().__init__(f"passkey required for {action}")
        self.action = action


class PasskeyInvalid(ValueError):
    def __init__(self, action: str) -> None:
        super().__init__(f"passkey assertion is invalid for {action}")
        self.action = action


def require_passkey(*, assertion: str | None, action: str) -> str:
    if assertion is None or not str(assertion).strip():
        raise PasskeyRequired(action)
    raw = str(assertion).strip()
    material = _extract_material(raw)
    if len(material) < _MIN_ASSERTION_LEN:
        raise PasskeyInvalid(action)
    if material.startswith("{") and material.endswith("}"):
        try:
            json.loads(material)
        except json.JSONDecodeError as exc:
            raise PasskeyInvalid(action) from exc
    elif _looks_like_base64url(material):
        try:
            base64.urlsafe_b64decode(material + "=" * (-len(material) % 4))
        except (binascii.Error, ValueError) as exc:
            raise PasskeyInvalid(action) from exc
    return raw


def _extract_material(raw: str) -> str:
    if raw.startswith("{"):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        if isinstance(payload, dict):
            response = payload.get("response")
            if isinstance(response, dict):
                for key in ("authenticatorData", "signature", "clientDataJSON"):
                    value = response.get(key)
                    if isinstance(value, str) and value:
                        return value
        return raw
    return raw


def _looks_like_base64url(value: str) -> bool:
    return bool(_BASE64URL.match(value)) and len(value) >= _MIN_ASSERTION_LEN
