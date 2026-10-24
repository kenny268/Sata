"""Fact-log subscription for outbound notifications (**TG-PO-10**)."""

from __future__ import annotations

from sate_factlog.log import FactLog

from sate_notifier.classifier import classify_event
from sate_notifier.delivery import DeliveryPolicy


def poll_notifications(
    log: FactLog,
    *,
    after_seq: int,
    policy: DeliveryPolicy,
    reader_id: str = "notifier-bot",
) -> list[dict[str, str]]:
    rows = log.poll(after_seq=after_seq, group_scope="A", reader_id=reader_id)
    messages: list[dict[str, str]] = []
    for row in rows:
        meta = classify_event(row.event_type)
        if not policy.should_deliver(meta["severity"], category=meta["category"]):
            continue
        messages.append(
            {
                "event_id": row.event_id,
                "text": f"[A-LIVE] {meta['category']} {meta['severity']}",
                "severity": meta["severity"],
            }
        )
    return messages
