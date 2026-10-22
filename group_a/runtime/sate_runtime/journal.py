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


def _check(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    return bool(item.get("name")) and isinstance(item.get("passed"), bool)


def _text_or_null(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
