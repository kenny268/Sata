"""Fact-log reads for /why and /digest (**TG-PO-11**, **TG-PO-12**)."""

from __future__ import annotations

from sate_factlog.log import FactLog, FactRecord


def find_record(log: FactLog, ref: str, *, reader_id: str = "notifier-bot") -> FactRecord | None:
    ref = ref.strip()
    if not ref:
        return None
    for scope in ("A", "GLOBAL", "B"):
        for row in log.poll(after_seq=0, group_scope=scope, reader_id=reader_id):
            if row.event_id == ref or row.correlation_id == ref:
                return row
            if ref in row.event_id or ref in row.correlation_id:
                return row
    return None


def explain_why(log: FactLog, ref: str) -> dict[str, str]:
    row = find_record(log, ref)
    if row is None:
        return {
            "text": f"No fact-log record for {ref!r}. Use the numeric id from a prior message.",
            "fact_ref": "",
        }
    return {
        "text": (
            f"[A-LIVE] WHY INFO\n"
            f"{row.event_type} seq={row.seq} at {row.occurred_at}\n"
            f"Fact ref: {row.event_id}"
        ),
        "fact_ref": row.event_id,
    }


def build_digest(log: FactLog, *, limit: int = 20) -> dict[str, str]:
    rows = log.poll(after_seq=0, group_scope="A", reader_id="notifier-bot")
    tail = rows[-limit:]
    if not tail:
        return {"text": "[A-SIM] SUMMARY INFO\nNo recent Group A events.", "count": "0"}
    lines = [f"[A-SIM] SUMMARY INFO\nLast {len(tail)} events:"]
    for row in tail:
        lines.append(f"- {row.event_type} {row.event_id}")
    return {"text": "\n".join(lines), "count": str(len(tail))}
