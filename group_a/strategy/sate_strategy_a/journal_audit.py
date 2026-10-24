"""Journal completeness audit (**A-PR-08**, Phase 20 exit)."""

from __future__ import annotations

from sate_factlog.log import FactLog


def journal_completeness_for_sessions(log: FactLog, *, session_ids: list[str], reader_id: str) -> float:
    if not session_ids:
        return 0.0
    rows = log.poll(after_seq=0, group_scope="A", reader_id=reader_id)
    matched = sum(
        1
        for session_id in session_ids
        if any(
            row.event_type == "journal"
            and (row.correlation_id.startswith(session_id) or session_id in row.event_id)
            for row in rows
        )
    )
    return matched / len(session_ids)
