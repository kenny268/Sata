"""Compose smoke: adequacy report + scenario suite."""

from __future__ import annotations

from sate_adequacy.report import build_adequacy_report
from sate_adequacy.runner import staging_evidence
from sate_adequacy.scenario_runner import run_scenario_suite


def main() -> None:
    suite = run_scenario_suite()
    if not suite.green:
        raise SystemExit("scenario suite not green")
    report = build_adequacy_report(staging_evidence())
    if not report.get("software_ready"):
        raise SystemExit("adequacy software not ready")
    print("adequacy ok", report["report_digest"][:12])


if __name__ == "__main__":
    main()
