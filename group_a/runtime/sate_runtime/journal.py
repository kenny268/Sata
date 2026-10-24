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


_AUDIT_KEYS = ("action", "credential_id", "key_id", "previous_key_id", "mode", "purpose")
_AUDIT_ACTIONS = frozenset({"inject", "rotate"})
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


def persist_reconciliation(log: FactLog, observation: dict[str, object], **identity: str) -> None:
    payload = _reconciliation(observation)
    log.append(
        event_id=str(identity["event_id"]),
        event_type="reconciliation",
        group_scope="A",
        occurred_at=str(identity["occurred_at"]),
        recorded_at=str(identity["recorded_at"]),
        correlation_id=str(identity["correlation_id"]),
        writer_id="kernel-a",
        payload=payload,
    )


_FAILURE_KEYS = ("kind", "intent_id", "correlation_id", "reason", "code")
_FAILURE_KINDS = frozenset({"protective_stop"})


def persist_execution_failure(log: FactLog, failure: dict[str, object], **identity: str) -> None:
    if set(failure) != set(_FAILURE_KEYS) or any(key in _SECRET_KEYS for key in failure):
        raise GateError("execution failure cannot carry a secret", code="secret")
    kind = str(failure["kind"])
    if kind not in _FAILURE_KINDS:
        raise GateError("execution failure is incomplete", code="record")
    for key in _FAILURE_KEYS:
        value = failure[key]
        if not isinstance(value, str) or value == "":
            raise GateError("execution failure is incomplete", code="record")
    if failure["correlation_id"] != f"A:{failure['intent_id']}":
        raise GateError("the order correlation is the idempotency key", code="record")
    log.append(
        event_id=str(identity["event_id"]),
        event_type="failure",
        group_scope="A",
        occurred_at=str(identity["occurred_at"]),
        recorded_at=str(identity["recorded_at"]),
        correlation_id=str(failure["correlation_id"]),
        writer_id="kernel-a",
        payload={key: failure[key] for key in _FAILURE_KEYS},
    )


_KILL_KEYS = ("command_id", "scope", "kill_level", "channel", "identity", "open_positions")
_MODE_KEYS = ("from_mode", "to_mode", "reason", "channel")
_HALT_KEYS = ("command_id", "scope", "state", "kill_level", "reason")
_CHECKIN_KEYS = ("channel", "strength", "days_without", "away_days")


def persist_kill_command(log: FactLog, command: dict[str, object], **identity: str) -> None:
    payload = _kill_command(command)
    log.append(
        event_id=str(identity["event_id"]),
        event_type="halt",
        group_scope=str(payload["scope"]) if payload["scope"] != "ALL" else "GLOBAL",
        occurred_at=str(identity["occurred_at"]),
        recorded_at=str(identity["recorded_at"]),
        correlation_id=str(identity["correlation_id"]),
        writer_id="kernel-a",
        payload=payload,
    )


def persist_mode_transition(log: FactLog, transition: dict[str, object], **identity: str) -> None:
    payload = _mode_transition(transition)
    log.append(
        event_id=str(identity["event_id"]),
        event_type="state_transition",
        group_scope="A",
        occurred_at=str(identity["occurred_at"]),
        recorded_at=str(identity["recorded_at"]),
        correlation_id=str(identity["correlation_id"]),
        writer_id="kernel-a",
        payload=payload,
    )


def persist_check_in(log: FactLog, event: dict[str, object], **identity: str) -> None:
    payload = _check_in(event)
    log.append(
        event_id=str(identity["event_id"]),
        event_type="check_in",
        group_scope="A",
        occurred_at=str(identity["occurred_at"]),
        recorded_at=str(identity["recorded_at"]),
        correlation_id=str(identity["correlation_id"]),
        writer_id="kernel-a",
        payload=payload,
    )


def persist_halt_state(log: FactLog, observation: dict[str, object], **identity: str) -> None:
    payload = _halt_state(observation)
    log.append(
        event_id=str(identity["event_id"]),
        event_type="halt",
        group_scope="A",
        occurred_at=str(identity["occurred_at"]),
        recorded_at=str(identity["recorded_at"]),
        correlation_id=str(identity["correlation_id"]),
        writer_id="kernel-a",
        payload=payload,
    )


def persist_credential_use(log: FactLog, audit: dict[str, object], **identity: str) -> None:
    if set(audit) != set(_AUDIT_KEYS):
        raise GateError("credential audit cannot carry a secret", code="secret")
    if any(key in _SECRET_KEYS for key in audit):
        raise GateError("credential audit cannot carry a secret", code="secret")
    action = str(audit["action"])
    mode = str(audit["mode"])
    if action not in _AUDIT_ACTIONS or mode not in {"SIM", "LIVE"}:
        raise GateError("credential audit is incomplete", code="record")
    for key in _AUDIT_KEYS:
        value = audit[key]
        if not isinstance(value, str):
            raise GateError("credential audit is incomplete", code="record")
        if key != "previous_key_id" and value == "":
            raise GateError("credential audit is incomplete", code="record")
    log.append(
        event_id=str(identity["event_id"]),
        event_type="credential_use",
        group_scope="A",
        occurred_at=str(identity["occurred_at"]),
        recorded_at=str(identity["recorded_at"]),
        correlation_id=str(identity["correlation_id"]),
        writer_id="kernel-a",
        payload={key: audit[key] for key in _AUDIT_KEYS},
    )


def _kill_command(command: dict[str, object]) -> dict[str, object]:
    if set(command) != set(_KILL_KEYS) or any(key in _SECRET_KEYS for key in command):
        raise GateError("kill command cannot carry a secret", code="secret")
    scope = str(command["scope"])
    if scope not in {"A", "B", "ALL"}:
        raise GateError("kill command is incomplete", code="record")
    level = str(command["kill_level"])
    if level not in {"K1", "K2", "K3"}:
        raise GateError("kill command is incomplete", code="record")
    for key in ("command_id", "channel", "identity", "open_positions"):
        value = command[key]
        if not isinstance(value, str):
            raise GateError("kill command is incomplete", code="record")
    return {key: command[key] for key in _KILL_KEYS}


def _mode_transition(transition: dict[str, object]) -> dict[str, object]:
    if set(transition) != set(_MODE_KEYS) or any(key in _SECRET_KEYS for key in transition):
        raise GateError("mode transition is incomplete", code="record")
    for key in _MODE_KEYS:
        if not isinstance(transition[key], str) or transition[key] == "":
            raise GateError("mode transition is incomplete", code="record")
    return {key: transition[key] for key in _MODE_KEYS}


def _check_in(event: dict[str, object]) -> dict[str, object]:
    if set(event) != set(_CHECKIN_KEYS) or any(key in _SECRET_KEYS for key in event):
        raise GateError("check-in record is incomplete", code="record")
    channel = str(event["channel"])
    strength = str(event["strength"])
    if channel not in {"web_passkey", "telegram_alive"}:
        raise GateError("check-in record is incomplete", code="record")
    if strength not in {"strong", "weak"}:
        raise GateError("check-in record is incomplete", code="record")
    for key in ("days_without", "away_days"):
        value = event[key]
        if not isinstance(value, str):
            raise GateError("check-in record is incomplete", code="record")
    return {key: event[key] for key in _CHECKIN_KEYS}


def _halt_state(observation: dict[str, object]) -> dict[str, object]:
    if set(observation) != set(_HALT_KEYS):
        raise GateError("halt state is incomplete", code="record")
    for key in _HALT_KEYS:
        if not isinstance(observation[key], str):
            raise GateError("halt state is incomplete", code="record")
    return {key: observation[key] for key in _HALT_KEYS}


def _reconciliation(observation: dict[str, object]) -> dict[str, object]:
    result = observation.get("result")
    halt = observation.get("halt")
    blocks = observation.get("blocks_new_risk")
    retry = observation.get("allows_retry")
    corrected = observation.get("corrected")
    manufactured = observation.get("manufactured_fill")
    diffs = observation.get("diffs")
    if result not in {"clean", "mismatch", "ambiguous", "outage"}:
        raise GateError("the reconciliation record is incomplete", code="record")
    if halt not in {"", "L2"} or not isinstance(blocks, bool) or not isinstance(retry, bool):
        raise GateError("the reconciliation record is incomplete", code="record")
    if not isinstance(corrected, bool) or manufactured is not False or not isinstance(diffs, list):
        raise GateError("reconciliation cannot manufacture a fill", code="fill")
    blocked = result in {"mismatch", "ambiguous"}
    if blocked and (blocks is not True or retry is not False or halt != "L2"):
        raise GateError("a mismatch blocks new risk immediately", code="halt")
    if result == "outage" and (blocks is not True or retry is not False):
        raise GateError("a mismatch blocks new risk immediately", code="halt")
    if result == "clean" and (blocks is not False or halt != "" or retry is not True):
        raise GateError("the reconciliation record is incomplete", code="record")
    return {
        "result": result,
        "halt": halt,
        "blocks_new_risk": blocks,
        "allows_retry": retry,
        "corrected": corrected,
        "manufactured_fill": False,
        "diffs": [_diff(item) for item in diffs],
    }


def _diff(item: object) -> dict[str, str]:
    if not isinstance(item, dict):
        raise GateError("the reconciliation record is incomplete", code="record")
    diff: dict[str, str] = {}
    for key in ("entity", "key", "field", "local", "broker"):
        value = item.get(key)
        if not isinstance(value, str):
            raise GateError("the reconciliation record is incomplete", code="record")
        diff[key] = value
    return diff


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
