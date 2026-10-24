import unittest

from sate_strategy_a.black_litterman import blend_views
from sate_strategy_a.regime import RegimeFilter


class RegimeAndSignalTests(unittest.TestCase):
    def test_regime_abstain_after_unstable_sessions(self) -> None:
        regime = RegimeFilter(unstable_limit=2)
        regime.record(stable=False)
        regime.record(stable=False)
        self.assertTrue(regime.should_abstain())

    def test_regime_blocked_when_n_unset(self) -> None:
        regime = RegimeFilter(unstable_limit=None)
        self.assertFalse(regime.tilt_enabled())

    def test_ts02_zero_advisory_uses_kalman(self) -> None:
        blend = blend_views(kalman_direction=1, advisory_view=None, regime_tilt=True)
        self.assertFalse(blend.advisory_used)
        self.assertEqual(blend.view, 1.0)


if __name__ == "__main__":
    unittest.main()
