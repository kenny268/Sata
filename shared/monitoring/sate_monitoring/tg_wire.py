"""Wire monitoring alerts to **TG-PO-15** message shape."""

from __future__ import annotations

from sate_monitoring.alerts import CriticalAlert


def to_health_payload(alert: CriticalAlert) -> dict[str, str]:
    if alert.code == "kernel_heartbeat_lost":
        return {
            "text": f"[{alert.group_scope}-LIVE] HEALTH CRITICAL\nKernel heartbeat: heartbeat_lost\n{alert.message}",
            "category": "HEALTH",
            "severity": "CRITICAL",
        }
    return {
        "text": f"[{alert.group_scope}-LIVE] ERROR CRITICAL\n{alert.code}: {alert.message[:200]}",
        "category": "ERROR",
        "severity": "CRITICAL",
    }
