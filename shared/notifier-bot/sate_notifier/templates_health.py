"""Health and error templates (**TG-PO-15**)."""

from __future__ import annotations


def health_status(*, scope: str, heartbeat_ok: bool, feed_latency_ms: str) -> dict[str, str]:
    severity = "INFO" if heartbeat_ok else "CRITICAL"
    tag = f"[{scope}-LIVE]"
    state = "ok" if heartbeat_ok else "heartbeat_lost"
    return {
        "text": f"{tag} HEALTH {severity}\nKernel heartbeat: {state}\nFeed latency: {feed_latency_ms} ms",
        "category": "HEALTH",
        "severity": severity,
    }


def error_notice(*, scope: str, code: str, detail: str) -> dict[str, str]:
    return {
        "text": f"[{scope}-LIVE] ERROR CRITICAL\n{code}: {detail[:200]}",
        "category": "ERROR",
        "severity": "CRITICAL",
    }
