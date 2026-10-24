"""CLI one-click adequacy report."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from sate_factlog.log import FactLog

from sate_adequacy.adequacy_log import persist_adequacy_report
from sate_adequacy.champion_runner import run_champion_from_files
from sate_adequacy.evidence import SimAdequacyEvidence
from sate_adequacy.export_dashboard import write_performance_dashboard
from sate_adequacy.fact_extract import evidence_from_fact_log
from sate_adequacy.report import build_adequacy_report


def staging_evidence() -> SimAdequacyEvidence:
    return SimAdequacyEvidence(
        generated_at=os.environ.get("SATE_ADEQUACY_AT", "2026-10-23T21:00:00Z"),
        sim_months_continuous=float(os.environ.get("SATE_SIM_MONTHS", "6.5")),
        reconciliation_clean_rate=float(os.environ.get("SATE_RECON_CLEAN_RATE", "0.96")),
        net_sharpe_after_costs=float(os.environ.get("SATE_NET_SHARPE", "1.25")),
        monthly_returns_net=(0.07, 0.065, 0.08),
        trade_count=int(os.environ.get("SATE_TRADE_COUNT", "220")),
        bootstrap_excess_lower_bound=0.01,
        l2_plus_unresolved_last_60d=0,
        parameter_changes_last_3_months=0,
        untradeable_session_rate=0.05,
        strategy_version_frozen="strategy-a@0.22.0",
        benchmark_return_twr=0.02,
        portfolio_return_twr=0.12,
    )


def load_evidence() -> SimAdequacyEvidence:
    evidence_path = os.environ.get("SATE_ADEQUACY_EVIDENCE_JSON")
    if evidence_path and Path(evidence_path).is_file():
        raw = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
        return SimAdequacyEvidence(**raw)
    fact_path = os.environ.get("SATE_ADEQUACY_FACTLOG_PATH")
    if fact_path and Path(fact_path).is_file():
        at = os.environ.get("SATE_ADEQUACY_AT", "2026-10-23T21:00:00Z")
        log = FactLog(
            sqlite3.connect(fact_path),
            writers=frozenset({"adequacy-a", "strategy-a", "cognitive-a"}),
            readers=frozenset({"adequacy-a", "strategy-a", "cognitive-a"}),
        )
        months = os.environ.get("SATE_SIM_MONTHS")
        return evidence_from_fact_log(
            log,
            reader_id="adequacy-a",
            as_of=at,
            sim_months_continuous=float(months) if months else None,
        )
    return staging_evidence()


def _optional_champion_verdict():
    champion_path = os.environ.get("SATE_CHAMPION_SHADOW_JSON")
    challenger_path = os.environ.get("SATE_CHALLENGER_SHADOW_JSON")
    if champion_path and challenger_path:
        return run_champion_from_files(
            champion_path=Path(champion_path),
            challenger_path=Path(challenger_path),
        )
    return None


def main() -> None:
    evidence = load_evidence()
    champion = _optional_champion_verdict()
    report = build_adequacy_report(evidence, champion=champion)
    out = Path(os.environ.get("SATE_ADEQUACY_REPORT_DIR", "/tmp/sate-adequacy"))
    out.mkdir(parents=True, exist_ok=True)
    path = out / "adequacy-report.json"
    path.write_text(json.dumps(report, sort_keys=True, indent=2), encoding="utf-8")
    write_performance_dashboard(evidence, destination=out)
    persist_path = os.environ.get("SATE_ADEQUACY_PERSIST_FACTLOG")
    if persist_path:
        at = evidence.generated_at
        log = FactLog(
            sqlite3.connect(persist_path),
            writers=frozenset({"adequacy-a"}),
            readers=frozenset({"adequacy-a"}),
        )
        persist_adequacy_report(
            log,
            event_id=f"adequacy-{at}",
            report=report,
            at=at,
        )
    print("adequacy report ok", report["report_digest"][:12])


if __name__ == "__main__":
    main()
