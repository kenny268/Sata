"""Fact-log subscription for outbound notifications (**TG-PO-10**)."""

from __future__ import annotations

from sate_factlog.log import FactLog

from sate_notifier.classifier import classify_event
from sate_notifier.delivery import DeliveryPolicy
from sate_notifier.tags import halt_line, scope_tag


def poll_notifications(
    log: FactLog,
    *,
    after_seq: int,
    policy: DeliveryPolicy,
    reader_id: str = "notifier-bot",
    mode: str = "",
    halt_command: str = "",
    partial_halt: bool = False,
) -> list[dict[str, str]]:
    rows = log.poll(after_seq=after_seq, group_scope="A", reader_id=reader_id)
    messages: list[dict[str, str]] = []
    for row in rows:
        meta = classify_event(row.event_type)
        if not policy.should_deliver(meta["severity"], category=meta["category"]):
            continue
        text = f"{scope_tag('A', mode)} {meta['category']} {meta['severity']}"
        banner = halt_line(halt_command, partial_halt=partial_halt)
        if banner:
            text = f"{text}\n{banner}"
        messages.append(
            {
                "event_id": row.event_id,
                "text": text,
                "severity": meta["severity"],
            }
        )
    return messages
