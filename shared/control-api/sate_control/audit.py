"""Every control action is an owner_action in the fact log."""

from __future__ import annotations

from sate_factlog.log import FactLog

_OWNER_KEYS = ("action", "scope", "channel", "principal", "detail")


def persist_owner_action(log: FactLog, record: dict[str, object], **identity: str) -> None:
    if set(record) != set(_OWNER_KEYS):
        raise ValueError("owner action record is incomplete")
    for key in _OWNER_KEYS:
        if not isinstance(record[key], str):
            raise ValueError("owner action record is incomplete")
    scope = str(record["scope"])
    group_scope = "GLOBAL" if scope == "ALL" else scope
    if group_scope not in {"A", "B", "GLOBAL"}:
        raise ValueError("owner action scope is invalid")
    log.append(
        event_id=str(identity["event_id"]),
        event_type="owner_action",
        group_scope=group_scope,
        occurred_at=str(identity["occurred_at"]),
        recorded_at=str(identity["recorded_at"]),
        correlation_id=str(identity["correlation_id"]),
        writer_id="control-api",
        payload={key: record[key] for key in _OWNER_KEYS},
    )
