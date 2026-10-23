import unittest

from sate_strategy_a.fx_calendar import calendar_loaded_for, current_fx_week
from sate_strategy_a.intent import build_intent
from sate_strategy_a.pre_kernel import MarketContext, validate_pre_kernel


def _intent() -> dict[str, object]:
    return build_intent(
        intent_id="i-1",
        account_mode="SIM",
        instrument="EURUSD",
        side="BUY",
        quantity="1",
        protective_stop="1.08",
        strategy_id="test",
        created_at="2026-10-18T21:00:00Z",
    )


def _context(**extra: object) -> MarketContext:
    values: dict[str, object] = {
        "tick_age_ms": 50,
        "swap_estimate": 0.1,
        "swap_budget": 5.0,
        "hold_includes_wednesday": False,
        "hold_through_close": False,
    }
    values.update(extra)
    return MarketContext(**values)  # type: ignore[arg-type]


class FxCalendarTests(unittest.TestCase):
    def test_week_opens_sunday_at_1700_new_york(self) -> None:
        self.assertEqual(current_fx_week("2026-10-18T21:00:00Z"), "2026-10-18")
        self.assertEqual(current_fx_week("2026-10-18T20:59:00Z"), "2026-10-11")
        self.assertEqual(current_fx_week("2026-10-24T21:00:00Z"), "2026-10-18")

    def test_stale_calendar_abstains_before_an_entry(self) -> None:
        blocked = validate_pre_kernel(
            _intent(),
            context=_context(as_of="2026-10-18T21:00:00Z", calendar_week="2026-10-11"),
        )
        self.assertIsNotNone(blocked)
        assert blocked is not None
        self.assertEqual(blocked.reason, "calendar_stale")
        loaded = validate_pre_kernel(
            _intent(),
            context=_context(as_of="2026-10-18T21:00:00Z", calendar_week="2026-10-18"),
        )
        self.assertIsNone(loaded)
        self.assertTrue(calendar_loaded_for("2026-10-18T21:00:00Z", "2026-10-18"))


if __name__ == "__main__":
    unittest.main()
