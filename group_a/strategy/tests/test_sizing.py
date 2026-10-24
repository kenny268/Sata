import unittest

from sate_strategy_a.sizing import size_position


class SizingTests(unittest.TestCase):
    def test_rejects_below_min_lot(self) -> None:
        result = size_position(
            capital_base="100",
            max_risk_pct="0.5",
            vol_scaled_risk="0.5",
            ramp_factor="1",
            stop_distance="0.0100",
            value_per_unit="100000",
            lot_step="0.01",
            min_lot="0.10",
            notional_cap_size="5",
            leverage_cap_size="5",
        )
        self.assertTrue(result.rejected)
        self.assertEqual(result.reason, "untradeable_at_this_capital")

    def test_floors_to_lot_step(self) -> None:
        result = size_position(
            capital_base="10000",
            max_risk_pct="0.5",
            vol_scaled_risk="0.5",
            ramp_factor="1",
            stop_distance="0.0050",
            value_per_unit="100000",
            lot_step="0.01",
            min_lot="0.01",
            notional_cap_size="5",
            leverage_cap_size="5",
        )
        self.assertFalse(result.rejected)
        self.assertEqual(result.quantity, "0.1")

    def test_kelly_is_ceiling_only(self) -> None:
        base = {
            "capital_base": "10000",
            "max_risk_pct": "1.0",
            "vol_scaled_risk": "1.0",
            "ramp_factor": "1",
            "stop_distance": "0.0050",
            "value_per_unit": "100000",
            "lot_step": "0.01",
            "min_lot": "0.01",
            "notional_cap_size": "10",
            "leverage_cap_size": "10",
        }
        uncapped = size_position(**base)
        capped = size_position(**base, kelly_ceiling="50")
        self.assertFalse(capped.rejected)
        self.assertLessEqual(float(capped.quantity), float(uncapped.quantity))

    def test_ramp_factor_scales_budget(self) -> None:
        common = {
            "capital_base": "10000",
            "max_risk_pct": "1.0",
            "vol_scaled_risk": "1.0",
            "stop_distance": "0.0050",
            "value_per_unit": "100000",
            "lot_step": "0.01",
            "min_lot": "0.01",
            "notional_cap_size": "10",
            "leverage_cap_size": "10",
        }
        full = size_position(**common, ramp_factor="1")
        half = size_position(**common, ramp_factor="0.5")
        self.assertGreaterEqual(float(full.quantity), float(half.quantity))


if __name__ == "__main__":
    unittest.main()
