"""Health and error templates (**TG-PO-15**)."""

from __future__ import annotations

from sate_notifier.tags import scope_tag


def health_status(
    *,
    scope: str,
    mode: str = "",
    heartbeat_ok: bool | None = None,
    feed_latency_ms: str = "unknown",
) -> dict[str, str]:
    if heartbeat_ok is None:
        severity = "INFO"
        state = "unknown"
    elif heartbeat_ok:
        severity = "INFO"
        state = "ok"
    else:
        severity = "CRITICAL"
        state = "heartbeat_lost"
    tag = scope_tag(scope, mode)
    latency = feed_latency_ms or "unknown"
    return {
        "text": f"{tag} HEALTH {severity}\nKernel heartbeat: {state}\nFeed latency: {latency} ms",
        "category": "HEALTH",
        "severity": severity,
    }


def error_notice(*, scope: str, code: str, detail: str, mode: str = "") -> dict[str, str]:
    return {
        "text": f"{scope_tag(scope, mode)} ERROR CRITICAL\n{code}: {detail[:200]}",
        "category": "ERROR",
        "severity": "CRITICAL",
    }
