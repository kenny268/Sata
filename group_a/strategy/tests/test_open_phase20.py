import unittest

from sate_strategy_a.engine import StrategyEngine
from sate_strategy_a.freshness import validate_freshness
from sate_strategy_a.instrument_profile import prefer_raw_commission
from sate_strategy_a.kalman import KalmanTickFilter
from sate_strategy_a.mp_infra import PromotionInfraChecklist
from sate_strategy_a.overnight import reject_overnight_carry
from sate_strategy_a.regime import RegimeFilter
from sate_strategy_a.scenarios import (
    ts01_valid_signal_to_intent,
    ts02_cognitive_down_kalman_continues,
    ts03_abstain_zero_view,
    ts09_swap_guard_blocks,
)
from sate_strategy_a.sim_loop import SimSizingBook, _sizing_dict
from sate_strategy_a.vol_risk import vol_scaled_risk_pct


class OpenPhase20Tests(unittest.TestCase):
    def test_freshness_blocks_stale(self) -> None:
        self.assertFalse(validate_freshness(age_ms=9000).ok)

    def test_uni_02_prefers_raw_commission_profile(self) -> None:
        profile = prefer_raw_commission(profile="raw_commission")
        self.assertEqual(profile.name, "raw_commission")
        self.assertEqual(prefer_raw_commission(profile="wide_spread").name, "wide_spread")

    def test_uni_03_overnight_rejected_by_default(self) -> None:
        self.assertTrue(reject_overnight_carry(hold_through_close=True, constitution_allows=False))

    def test_vol_scaled_risk_shrinks_when_vol_rises(self) -> None:
        scaled = vol_scaled_risk_pct(base_pct="0.5", atr="0.0020", baseline_atr="0.0010")
        self.assertEqual(scaled, "0.25")

    def test_ts_scenarios(self) -> None:
        engine = StrategyEngine(
            account_mode="SIM",
            rung="SIM",
            kalman=KalmanTickFilter(innovation_threshold_sigma=0.03),
            regime=RegimeFilter(unstable_limit=5),
        )
        prices = [1.0850, 1.0850] + [1.1200] * 8
        ts01 = ts01_valid_signal_to_intent(engine, prices=prices)
        self.assertIn("pre_kernel_ok", ts01.steps)
        self.assertIn("zero_advisory_kalman_ok", ts02_cognitive_down_kalman_continues().steps)
        self.assertEqual(ts03_abstain_zero_view().category, "ABSTAIN")
        self.assertIn("swap_rejected", ts09_swap_guard_blocks().steps)

    def test_mp_infra_checklist(self) -> None:
        checklist = PromotionInfraChecklist()
        checklist.record_mp01_bootstrap_gate()
        checklist.record_mp02_shadow_decisions()
        checklist.record_mp03_no_loosen()
        self.assertTrue(checklist.gate_met())

    def test_sizing_uses_vol_scale_helper(self) -> None:
        book = SimSizingBook(vol_atr="0.0020", baseline_atr="0.0010")
        sizing = _sizing_dict(book)
        self.assertEqual(sizing["vol_scaled_risk"], "0.25")


if __name__ == "__main__":
    unittest.main()
