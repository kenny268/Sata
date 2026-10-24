"""Champion/challenger shadow runner (**A-P1-05**)."""

from __future__ import annotations

from dataclasses import dataclass

from sate_strategy_a.promotion import FROZEN_KALMAN_INNOVATION_SIGMA, live_parameter_change_allowed


@dataclass(frozen=True)
class ShadowMetrics:
    label: str
    rank_corr: float | None
    signals_ingested: int
    mean_shadow_c: float | None


@dataclass(frozen=True)
class ChampionVerdict:
    champion: str
    challenger: str
    winner: str
    promotion_params_frozen: bool
    detail: str


def compare_champion_challenger(
    champion: ShadowMetrics,
    challenger: ShadowMetrics,
) -> ChampionVerdict:
    frozen = not live_parameter_change_allowed()
    c_score = champion.rank_corr if champion.rank_corr is not None else -1.0
    ch_score = challenger.rank_corr if challenger.rank_corr is not None else -1.0
    if ch_score > c_score:
        winner = challenger.label
        detail = "challenger rank correlation higher in shadow"
    elif c_score > ch_score:
        winner = champion.label
        detail = "champion retains shadow lead"
    else:
        winner = champion.label
        detail = "tie — champion retained"
    if frozen:
        detail = f"{detail}; kalman sigma frozen at {FROZEN_KALMAN_INNOVATION_SIGMA}"
    return ChampionVerdict(
        champion=champion.label,
        challenger=challenger.label,
        winner=winner,
        promotion_params_frozen=frozen,
        detail=detail,
    )
