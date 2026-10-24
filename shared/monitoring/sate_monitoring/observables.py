"""§14.1 observable registry from component state snapshots."""

from __future__ import annotations

from sate_monitoring.metrics import MetricSample, sample

_DOMAINS = (
    "kernel",
    "broker",
    "market_data",
    "reconciliation",
    "risk",
    "capital",
    "treasury",
    "deployment",
    "security",
    "fact_log",
    "backup",
    "check_in",
)


def collect_observables(state: dict[str, object], *, observed_at: str) -> list[MetricSample]:
    """Build metric samples for all §14.1 domains present in ``state``."""
    out: list[MetricSample] = []
    scope = str(state.get("group_scope", "A"))
    mapping: list[tuple[str, str, object]] = [
        ("kernel", "heartbeat_ok", state.get("heartbeat_ok", 1)),
        ("kernel", "halt_level", state.get("halt_level", "")),
        ("broker", "adapter_state", state.get("adapter_state", "unknown")),
        ("market_data", "feed_latency_ms", state.get("feed_latency_ms", 0)),
        ("reconciliation", "recon_clean", state.get("recon_clean", 0)),
        ("risk", "drawdown_pct", state.get("drawdown_pct", 0)),
        ("capital", "rcb_ratio", state.get("rcb_ratio", 0)),
        ("treasury", "obligations_open", state.get("obligations_open", 0)),
        ("deployment", "artifact_hash_ok", state.get("artifact_hash_ok", 1)),
        ("security", "signature_failures", state.get("signature_failures", 0)),
        ("fact_log", "chain_ok", state.get("chain_ok", 1)),
        ("backup", "last_success_ok", 1 if state.get("backup_last_success") else 0),
        ("check_in", "days_since_presence", state.get("days_since_presence", 0)),
    ]
    for domain, name, value in mapping:
        if domain not in _DOMAINS:
            continue
        numeric = value if isinstance(value, (int, float)) else (1.0 if value else 0.0)
        if isinstance(value, str) and value.isdigit():
            numeric = float(value)
        out.append(sample(f"{domain}.{name}", float(numeric), group_scope=scope, observed_at=observed_at))
    return out
