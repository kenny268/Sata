"""Rolling SIM ops evidence (**A-SIM-02**, **A-SIM-05**, **A-SIM-08**)."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from sate_factlog.log import FactLog

WRITER_ID = "sim-ops-a"


@dataclass(frozen=True)
class SimDayRecord:
    day: str
    sessions: int
    recon_clean_sessions: int
    trades: int
    untradeable_sessions: int
    l2_plus_events: int
    floor_sizing: bool = True


@dataclass(frozen=True)
class LedgerRollup:
    days: int
    reconciliation_clean_rate: float
    trade_count: int
    untradeable_session_rate: float
    l2_plus_events: int


def persist_period_start(log: FactLog, *, started_at: str, recorded_at: str) -> None:
    log.append(
        event_id=f"sim-period-start-{started_at}",
        event_type="deployment",
        group_scope="A",
        occurred_at=started_at,
        recorded_at=recorded_at,
        correlation_id="sim-period",
        writer_id=WRITER_ID,
        payload={"kind": "sim_period_start", "started_at": started_at},
    )


def persist_day(log: FactLog, record: SimDayRecord, *, at: str) -> None:
    log.append(
        event_id=f"sim-day-{record.day}",
        event_type="owner_action",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id="sim-ops-ledger",
        writer_id=WRITER_ID,
        payload={"kind": "sim_day", **asdict(record)},
    )


def load_days_from_log(log: FactLog, *, reader_id: str, as_of: str) -> list[SimDayRecord]:
    rows = log.replay_through(group_scope="A", as_of=as_of, reader_id=reader_id)
    days: list[SimDayRecord] = []
    for row in rows:
        if row.payload.get("kind") != "sim_day":
            continue
        days.append(
            SimDayRecord(
                day=str(row.payload["day"]),
                sessions=int(row.payload["sessions"]),
                recon_clean_sessions=int(row.payload["recon_clean_sessions"]),
                trades=int(row.payload["trades"]),
                untradeable_sessions=int(row.payload["untradeable_sessions"]),
                l2_plus_events=int(row.payload["l2_plus_events"]),
                floor_sizing=bool(row.payload.get("floor_sizing", True)),
            )
        )
    return days


def period_start_from_log(log: FactLog, *, reader_id: str, as_of: str) -> str | None:
    rows = log.replay_through(group_scope="A", as_of=as_of, reader_id=reader_id)
    for row in reversed(rows):
        if row.payload.get("kind") == "sim_period_start":
            return str(row.payload["started_at"])
    return None


def persist_session(
    log: FactLog,
    *,
    day: str,
    session_id: str,
    journal_logged: bool,
    order_placed: bool,
    verdict: str,
    at: str,
) -> None:
    log.append(
        event_id=f"sim-session-{session_id}",
        event_type="owner_action",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id="sim-ops-ledger",
        writer_id=WRITER_ID,
        payload={
            "kind": "sim_session",
            "day": day,
            "session_id": session_id,
            "journal_logged": journal_logged,
            "order_placed": order_placed,
            "verdict": verdict,
            "recon_clean": journal_logged,
            "untradeable": verdict == "Abstain" and not order_placed,
        },
    )


def _sessions_from_log(log: FactLog, *, reader_id: str, as_of: str) -> list[dict[str, object]]:
    rows = log.replay_through(group_scope="A", as_of=as_of, reader_id=reader_id)
    sessions: list[dict[str, object]] = []
    for row in rows:
        if row.payload.get("kind") != "sim_session":
            continue
        sessions.append(dict(row.payload))
    return sessions


def days_from_log(log: FactLog, *, reader_id: str, as_of: str) -> list[SimDayRecord]:
    explicit = {day.day: day for day in load_days_from_log(log, reader_id=reader_id, as_of=as_of)}
    buckets: dict[str, dict[str, int]] = {}
    for item in _sessions_from_log(log, reader_id=reader_id, as_of=as_of):
        day = str(item["day"])
        bucket = buckets.setdefault(
            day,
            {
                "sessions": 0,
                "recon_clean_sessions": 0,
                "trades": 0,
                "untradeable_sessions": 0,
                "l2_plus_events": 0,
            },
        )
        bucket["sessions"] += 1
        if item.get("recon_clean"):
            bucket["recon_clean_sessions"] += 1
        if item.get("order_placed"):
            bucket["trades"] += 1
        if item.get("untradeable"):
            bucket["untradeable_sessions"] += 1
    merged: dict[str, SimDayRecord] = dict(explicit)
    for day, bucket in buckets.items():
        if day in merged:
            existing = merged[day]
            merged[day] = SimDayRecord(
                day=day,
                sessions=existing.sessions + bucket["sessions"],
                recon_clean_sessions=existing.recon_clean_sessions + bucket["recon_clean_sessions"],
                trades=existing.trades + bucket["trades"],
                untradeable_sessions=existing.untradeable_sessions + bucket["untradeable_sessions"],
                l2_plus_events=existing.l2_plus_events + bucket["l2_plus_events"],
                floor_sizing=existing.floor_sizing,
            )
        else:
            merged[day] = SimDayRecord(
                day=day,
                sessions=bucket["sessions"],
                recon_clean_sessions=bucket["recon_clean_sessions"],
                trades=bucket["trades"],
                untradeable_sessions=bucket["untradeable_sessions"],
                l2_plus_events=bucket["l2_plus_events"],
                floor_sizing=True,
            )
    return sorted(merged.values(), key=lambda record: record.day)


def rollup_from_log(log: FactLog, *, reader_id: str, as_of: str) -> LedgerRollup:
    return rollup(days_from_log(log, reader_id=reader_id, as_of=as_of))


def rollup(days: list[SimDayRecord]) -> LedgerRollup:
    if not days:
        return LedgerRollup(
            days=0,
            reconciliation_clean_rate=0.0,
            trade_count=0,
            untradeable_session_rate=1.0,
            l2_plus_events=0,
        )
    sessions = sum(day.sessions for day in days)
    recon_clean = sum(day.recon_clean_sessions for day in days)
    trades = sum(day.trades for day in days)
    untradeable = sum(day.untradeable_sessions for day in days)
    l2 = sum(day.l2_plus_events for day in days)
    return LedgerRollup(
        days=len(days),
        reconciliation_clean_rate=recon_clean / max(sessions, 1),
        trade_count=trades,
        untradeable_session_rate=untradeable / max(sessions, 1),
        l2_plus_events=l2,
    )
