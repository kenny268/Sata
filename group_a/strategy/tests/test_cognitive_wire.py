"""MOD **TS-02–03** via cognitive ingest boundary."""

from __future__ import annotations

import unittest

from sate_cognitive.fixtures import generate_keypair, signed_signal
from sate_cognitive.ingest import ingest_signal

from sate_strategy_a.black_litterman import blend_views
from sate_strategy_a.cognitive_wire import advisory_view_for_blend
from sate_strategy_a.scenarios import ts03_abstain_zero_view


class CognitiveWireTests(unittest.TestCase):
    def setUp(self) -> None:
        self.private, self.public = generate_keypair()

    def test_ts02_invalid_signal_zero_trading_view(self) -> None:
        bad = {"signal_id": "x"}
        result = ingest_signal(bad, now="2026-10-23T12:00:00Z", public_key=self.public)
        view = advisory_view_for_blend(result)
        self.assertIsNone(view)
        blend = blend_views(kalman_direction=1, advisory_view=view, regime_tilt=True)
        self.assertFalse(blend.advisory_used)
        self.assertEqual(blend.view, 1.0)

    def test_ts03_abstain_category(self) -> None:
        decision = ts03_abstain_zero_view()
        self.assertEqual(decision.category, "ABSTAIN")

    def test_valid_shadow_signal_still_zero_trading_view(self) -> None:
        signal = signed_signal(self.private)
        result = ingest_signal(
            signal,
            now="2026-10-23T12:00:00Z",
            public_key=self.public,
            account_mode="SIM",
        )
        self.assertTrue(result.ok)
        self.assertGreater(result.shadow_q, 0.0)
        self.assertIsNone(advisory_view_for_blend(result))


if __name__ == "__main__":
    unittest.main()
