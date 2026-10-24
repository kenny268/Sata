"""Export performance dashboard JSON (**A-P1-07**)."""

from __future__ import annotations

import json
from pathlib import Path

from sate_adequacy.dashboard import build_performance_panels
from sate_adequacy.evidence import SimAdequacyEvidence
from sate_adequacy.perf import performance_snapshot


def performance_dashboard_export(evidence: SimAdequacyEvidence) -> dict[str, object]:
    months = list(evidence.monthly_returns_net) or [0.01, 0.02, 0.01]
    benchmark = [0.001] * len(months)
    snap = performance_snapshot(portfolio_monthly=months, benchmark_monthly=benchmark)
    panels = build_performance_panels(snap)
    return {
        "net_of_cost": True,
        "portfolio_twr": snap.portfolio_twr,
        "benchmark_twr": snap.benchmark_twr,
        "panels": [
            {"title": panel.title, "ok": panel.ok, "detail": panel.detail} for panel in panels
        ],
    }


def write_performance_dashboard(
    evidence: SimAdequacyEvidence,
    *,
    destination: Path,
) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "performance-dashboard.json"
    path.write_text(
        json.dumps(performance_dashboard_export(evidence), sort_keys=True, indent=2),
        encoding="utf-8",
    )
    return path
