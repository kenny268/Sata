import unittest

from sate_strategy_a.backtest import run_vectorised_backtest
from sate_strategy_a.costs import EURUSD_COSTS


class BacktestTests(unittest.TestCase):
    def test_vectorised_backtest_runs_without_llm(self) -> None:
        prices = [1.08 + (index % 5) * 0.0005 for index in range(100)]
        result = run_vectorised_backtest(prices, costs=EURUSD_COSTS)
        self.assertGreaterEqual(result.trades, 0)


if __name__ == "__main__":
    unittest.main()
