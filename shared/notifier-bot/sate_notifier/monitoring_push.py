"""Deliver monitoring **TG-PO-15** payloads via notifier delivery policy."""

from __future__ import annotations

from sate_notifier.delivery import DeliveryPolicy


def deliver_monitoring_payload(payload: dict[str, str], policy: DeliveryPolicy, *, now: float) -> bool:
    severity = payload.get("severity", "INFO")
    category = payload.get("category", "")
    if not policy.should_deliver(severity, now=now, category=category):
        return False
    return bool(payload.get("text"))
