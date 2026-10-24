"""Demo marathon shadow signal batch (**Phase 21**)."""

from __future__ import annotations

import os
from pathlib import Path

from sate_cognitive.fixtures import generate_keypair, signed_signal
from sate_cognitive.shadow import ShadowAccumulator
from sate_cognitive.shadow_log import persist_weekly_shadow
from sate_cognitive.shadow_store import save_accumulator
from sate_cognitive.weekly_runner import write_weekly_report

from sate_strategy_a.sim_cognitive import SimCognitiveShadow


def build_marathon_shadow(*, week: str, sessions: int) -> tuple[SimCognitiveShadow, list[dict[str, object] | None]]:
    private, public = generate_keypair()
    accumulator = ShadowAccumulator(week=week)
    shadow = SimCognitiveShadow(public_key=public, week=week, accumulator=accumulator)
    signals: list[dict[str, object] | None] = []
    for index in range(sessions):
        if index % 7 == 6:
            signals.append(
                signed_signal(
                    private,
                    signal_id=f"marathon-toxic-{index}",
                    evidence_refs=["IGNORE PREVIOUS"],
                )
            )
        else:
            q = 0.12 if index % 2 == 0 else -0.08
            signals.append(
                signed_signal(
                    private,
                    signal_id=f"marathon-{index}",
                    q=q,
                )
            )
    return shadow, signals


def finalize_marathon_shadow(
    shadow: SimCognitiveShadow,
    *,
    at: str,
    log,
) -> None:
    report = shadow.accumulator.weekly_report()
    state_path = Path(os.environ.get("SATE_SHADOW_STATE_FILE", "/tmp/sate-shadow/state.json"))
    save_accumulator(shadow.accumulator, state_path)
    write_weekly_report(report)
    if log is not None:
        persist_weekly_shadow(
            log,
            event_id=f"shadow-weekly-{report.week}",
            report=report,
            at=at,
        )
