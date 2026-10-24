"""Shadow evaluation export **A-COG-04** (methodology only; threshold not invented)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sate_cognitive.gate import CG_LIVE_THRESHOLD_DEFINED


@dataclass
class ShadowSample:
    signal_id: str
    shadow_q: float
    outcome: float
    shadow_c: float = 0.0


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    den_x = sum((x - mean_x) ** 2 for x in xs) ** 0.5
    den_y = sum((y - mean_y) ** 2 for y in ys) ** 0.5
    if den_x == 0.0 or den_y == 0.0:
        return None
    return num / (den_x * den_y)


@dataclass
class ShadowReport:
    week: str
    signals_ingested: int
    abstains: int
    rank_corr_vs_baseline: float | None
    mean_shadow_c: float | None = None
    pnl_delta_vs_zero_baseline: float = 0.0
    methodology: str = "advisory_zero_baseline"
    cg_live_threshold_defined: bool = CG_LIVE_THRESHOLD_DEFINED

    def export(self) -> dict[str, object]:
        return {
            "week": self.week,
            "signals_ingested": self.signals_ingested,
            "abstains": self.abstains,
            "rank_corr_vs_baseline": self.rank_corr_vs_baseline,
            "mean_shadow_c": self.mean_shadow_c,
            "pnl_delta_vs_zero_baseline": self.pnl_delta_vs_zero_baseline,
            "methodology": self.methodology,
            "cg_live_threshold_defined": self.cg_live_threshold_defined,
        }


@dataclass
class ShadowAccumulator:
    week: str
    ingested: int = 0
    abstains: int = 0
    samples: list[ShadowSample] = field(default_factory=list)
    shadow_c_sum: float = 0.0

    def record_ingest(
        self,
        *,
        ok: bool,
        signal_id: str,
        shadow_q: float,
        shadow_c: float = 0.0,
    ) -> None:
        if ok:
            self.ingested += 1
            self.shadow_c_sum += shadow_c
            self.samples.append(
                ShadowSample(signal_id=signal_id, shadow_q=shadow_q, outcome=0.0, shadow_c=shadow_c)
            )
        else:
            self.abstains += 1

    def attach_outcome(self, signal_id: str, outcome: float) -> None:
        for sample in reversed(self.samples):
            if sample.signal_id == signal_id:
                sample.outcome = outcome
                return

    def weekly_report(self) -> ShadowReport:
        xs = [sample.shadow_q for sample in self.samples]
        ys = [sample.outcome for sample in self.samples]
        mean_c = self.shadow_c_sum / self.ingested if self.ingested else None
        return ShadowReport(
            week=self.week,
            signals_ingested=self.ingested,
            abstains=self.abstains,
            rank_corr_vs_baseline=_pearson(xs, ys),
            mean_shadow_c=mean_c,
            pnl_delta_vs_zero_baseline=0.0,
        )
