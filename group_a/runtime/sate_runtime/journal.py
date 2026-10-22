"""Persist a schema-complete verdict, then allow the mock adapter to see it."""

from __future__ import annotations

from sate_factlog.log import FactLog

_APPROVED = frozenset({"Allow", "AllowWithSize"})
_DECISIONS = frozenset({"Allow", "AllowWithSize", "Reject", "Throttle"})
_REQUIRED = (
    "intent_id",
    "kernel_version",
    "constitution_version",
    "decision",
    "checks",
    "issued_at",
)


class GateError(ValueError):
    """The verdict is missing or it does not allow a broker order."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def persist_verdict(log: FactLog, verdict: dict[str, object], **identity: str) -> None:
    if verdict.get("group") not in (None, "A"):
        raise GateError("a kernel A verdict stays on group A", code="scope")
    log.append(
        event_id=str(identity["event_id"]),
        event_type="verdict",
        group_scope="A",
        occurred_at=str(identity["occurred_at"]),
        recorded_at=str(identity["recorded_at"]),
        correlation_id=str(identity["correlation_id"]),
        writer_id="kernel-a",
        payload=_record(verdict),
    )


def submit_persisted(verdict: dict[str, object], *, persisted: bool) -> str:
    if not persisted:
        raise GateError("verdict is not in the fact log", code="fact_log")
    decision = str(verdict.get("decision", ""))
    if decision not in _APPROVED:
        raise GateError("no broker order without an allow verdict", code="verdict")
    return str(verdict["intent_id"])


def _record(verdict: dict[str, object]) -> dict[str, object]:
    for key in _REQUIRED:
        if verdict.get(key) in (None, ""):
            raise GateError("verdict record is incomplete", code="record")
    decision = str(verdict["decision"])
    if decision not in _DECISIONS:
        raise GateError("verdict record is incomplete", code="record")
    checks = verdict["checks"]
    if not isinstance(checks, list) or any(not _check(item) for item in checks):
        raise GateError("verdict record is incomplete", code="record")
    latency = verdict.get("latency_us")
    if latency is not None and not isinstance(latency, int):
        raise GateError("verdict record is incomplete", code="record")
    return {
        "intent_id": str(verdict["intent_id"]),
        "kernel_version": str(verdict["kernel_version"]),
        "constitution_version": str(verdict["constitution_version"]),
        "decision": decision,
        "approved_quantity": _text_or_null(verdict.get("approved_quantity")),
        "reject_reason": _text_or_null(verdict.get("reject_reason")),
        "checks": checks,
        "halt_level": _text_or_null(verdict.get("halt_level")),
        "kill_state": _text_or_null(verdict.get("kill_state")),
        "latency_us": latency,
        "issued_at": str(verdict["issued_at"]),
    }


_SECRET_KEYS = frozenset({"password", "login", "secret", "server", "token", "api_key"})
_ORDER_STATES = frozenset({"New", "Submitted", "Partial", "Filled", "Cancelled", "Failed"})
_ORDER_KINDS = frozenset({"submit", "partial", "fill", "cancel", "fail", "timeout"})
_SIDES = frozenset({"BUY", "SELL"})
_LIFECYCLE_KEYS = (
    "intent_id",
    "client_id",
    "correlation_id",
    "state",
    "instrument",
    "side",
    "quantity",
    "filled",
    "remainder",
    "broker_id",
    "kind",
)


def persist_lifecycle(log: FactLog, event: dict[str, object], **identity: str) -> None:
    payload = _lifecycle(event)
    if str(identity["correlation_id"]) != payload["correlation_id"]:
        raise GateError("the order correlation is the idempotency key", code="record")
    event_type = "fills" if payload["kind"] in {"partial", "fill"} else "orders"
    log.append(
        event_id=str(identity["event_id"]),
        event_type=event_type,
        group_scope="A",
        occurred_at=str(identity["occurred_at"]),
        recorded_at=str(identity["recorded_at"]),
        correlation_id=str(payload["correlation_id"]),
        writer_id="kernel-a",
        payload=payload,
    )


def _lifecycle(event: dict[str, object]) -> dict[str, object]:
    if set(event) != set(_LIFECYCLE_KEYS) or any(key in _SECRET_KEYS for key in event):
        raise GateError("the order record is incomplete", code="record")
    kind = str(event["kind"])
    state = str(event["state"])
    side = str(event["side"])
    intent_id = str(event["intent_id"])
    if kind not in _ORDER_KINDS or state not in _ORDER_STATES or side not in _SIDES:
        raise GateError("the order record is incomplete", code="record")
    if event["correlation_id"] != f"A:{intent_id}" or event["client_id"] != intent_id:
        raise GateError("the order correlation is the idempotency key", code="record")
    broker_id = event["broker_id"]
    if broker_id is not None and (not isinstance(broker_id, str) or broker_id == ""):
        raise GateError("the order record is incomplete", code="record")
    payload: dict[str, object] = {}
    for key in _LIFECYCLE_KEYS:
        if key == "broker_id":
            payload[key] = broker_id
            continue
        value = event[key]
        if not isinstance(value, str) or value == "":
            raise GateError("the order record is incomplete", code="record")
        if key in {"quantity", "filled", "remainder"} and not _decimal(value):
            raise GateError("the order record is incomplete", code="record")
        payload[key] = value
    return payload


def _decimal(value: str) -> bool:
    if value.endswith("."):
        return False
    whole, dot, frac = value.partition(".")
    if not whole.isdigit() or (dot and not frac.isdigit()):
        return False
    return whole == "0" or not whole.startswith("0")


def _check(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    return bool(item.get("name")) and isinstance(item.get("passed"), bool)


def _text_or_null(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
