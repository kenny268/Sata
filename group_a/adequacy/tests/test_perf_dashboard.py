import unittest

from sate_adequacy.dashboard import build_performance_panels
from sate_adequacy.perf import bootstrap_excess_lower_bound, performance_snapshot, sharpe_ratio


class PerfDashboardTests(unittest.TestCase):
    def test_net_sharpe_and_panels(self) -> None:
        portfolio = [0.02, 0.03, 0.01, 0.025, 0.015, 0.02]
        benchmark = [0.001] * len(portfolio)
        snap = performance_snapshot(portfolio_monthly=portfolio, benchmark_monthly=benchmark)
        panels = build_performance_panels(snap)
        self.assertEqual(len(panels), 3)
        self.assertGreater(sharpe_ratio(portfolio), 0.0)
        self.assertGreater(bootstrap_excess_lower_bound(portfolio, benchmark), 0.0)


if __name__ == "__main__":
    unittest.main()
