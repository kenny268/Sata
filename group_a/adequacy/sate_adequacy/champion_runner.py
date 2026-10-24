"""Run champion/challenger from shadow JSON exports (**A-P1-05**)."""

from __future__ import annotations

import json
from pathlib import Path

from sate_adequacy.champion import ChampionVerdict, ShadowMetrics, compare_champion_challenger


def metrics_from_shadow_export(path: Path, *, label: str) -> ShadowMetrics:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return ShadowMetrics(
        label=label,
        rank_corr=raw.get("rank_corr_vs_baseline"),
        signals_ingested=int(raw.get("signals_ingested", 0)),
        mean_shadow_c=raw.get("mean_shadow_c"),
    )


def run_champion_from_files(
    *,
    champion_path: Path,
    challenger_path: Path,
) -> ChampionVerdict:
    champion = metrics_from_shadow_export(champion_path, label="champion")
    challenger = metrics_from_shadow_export(challenger_path, label="challenger")
    return compare_champion_challenger(champion, challenger)
