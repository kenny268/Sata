"""Apply Group A projections only from fact-log records."""

from __future__ import annotations

from sate_factlog.log import FactLog

from sate_identity.registry import IdentityRegistry, consume_fact_event


def submit_capital_state(
    log: FactLog,
    payload: dict[str, object],
    *,
    event_id: str,
    occurred_at: str,
    recorded_at: str,
    correlation_id: str,
) -> int:
    record = log.append(
        event_id=event_id,
        event_type="capital_state",
        group_scope="A",
        occurred_at=occurred_at,
        recorded_at=recorded_at,
        correlation_id=correlation_id,
        writer_id="identity",
        payload=payload,
    )
    return record.seq


def submit_registration(
    log: FactLog,
    payload: dict[str, object],
    *,
    event_id: str,
    occurred_at: str,
    recorded_at: str,
    correlation_id: str,
) -> int:
    record = log.append(
        event_id=event_id,
        event_type="state_transition",
        group_scope="A",
        occurred_at=occurred_at,
        recorded_at=recorded_at,
        correlation_id=correlation_id,
        writer_id="identity",
        payload=payload,
    )
    return record.seq


def apply_pending(log: FactLog, registry: IdentityRegistry, after_seq: int) -> int:
    """Project new Group A events. Returns the cursor to store."""
    cursor = after_seq
    for record in log.poll(after_seq=after_seq, group_scope="A", reader_id="identity"):
        if record.event_type == "capital_state" and "projection_id" in record.payload:
            projection_id = str(record.payload["projection_id"])
            if not registry.has_risk_projection(projection_id):
                consume_fact_event(registry, record.as_envelope())
        elif record.event_type == "state_transition":
            _apply_transition(registry, record.payload)
        cursor = record.seq
    return cursor


def _apply_transition(registry: IdentityRegistry, payload: dict[str, object]) -> None:
    profile_id = str(payload["profile_id"])
    login = str(payload["account_login"])
    server = str(payload["server"])
    recorded_at = str(payload["recorded_at"])
    current = registry.current(profile_id)
    if payload.get("kind") == "fingerprint":
        if current is None:
            raise ValueError("fingerprint change requires a registered profile")
        unchanged = (
            current["account_login"] == login
            and current["server"] == server
            and current["recorded_at"] == recorded_at
        )
        if not unchanged:
            registry.change_fingerprint(
                profile_id=profile_id,
                account_login=login,
                server=server,
                recorded_at=recorded_at,
            )
        return
    if current is None:
        registry.register(
            profile_id=profile_id,
            broker_id=str(payload["broker_id"]),
            account_login=login,
            server=server,
            recorded_at=recorded_at,
        )
        return
    if current["account_login"] != login or current["server"] != server:
        raise ValueError("registration conflicts with the stored fingerprint")
