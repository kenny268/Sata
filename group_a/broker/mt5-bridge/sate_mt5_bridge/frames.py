"""ZeroMQ message body. The socket stays closed while the Windows host is open."""

from __future__ import annotations

import json

from sate_mt5_bridge.errors import AdapterError

_FORBIDDEN = frozenset({"password", "secret", "token", "api_key"})


def encode_frame(op: str, payload: dict[str, object]) -> bytes:
    if _FORBIDDEN & set(payload):
        raise AdapterError("the bridge frame cannot carry a credential", code="credential")
    body = {"op": op, "payload": payload}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def decode_frame(frame: bytes) -> dict[str, object]:
    try:
        body = json.loads(frame.decode())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdapterError("the bridge frame is malformed", code="malformed") from exc
    if not isinstance(body, dict) or not isinstance(body.get("payload"), dict):
        raise AdapterError("the bridge frame is malformed", code="malformed")
    if _FORBIDDEN & set(body["payload"]):
        raise AdapterError("the bridge frame cannot carry a credential", code="credential")
    return body


def refuse_dealer(endpoint: str) -> None:
    """A dealer socket is the transport. This host has no Windows terminal to dial."""
    if not endpoint.startswith(("tcp://", "ipc://")):
        raise AdapterError("the bridge endpoint is malformed", code="transport")
    raise AdapterError("Windows terminal endpoint is not provisioned", code="host")
