"""Global halt protocol and kill drills."""

from __future__ import annotations

import unittest

from sate_halt.c1_runbook import KillView, run_c1
from sate_halt.protocol import HaltState
from sate_halt.service import Coordinator


class HaltCoordinatorTests(unittest.TestCase):
    def test_inv06_unreachable_b_never_becomes_all(self) -> None:
        coordinator = Coordinator()
        command = coordinator.issue(
            command_id="hc-1",
            scope="ALL",
            kill_level="K2",
            reason="test",
            channel="web",
            identity="owner",
            b_reachable=False,
        )
        coordinator.ack_a(command.command_id)
        self.assertEqual(coordinator.mark_b_unreachable(command.command_id), HaltState.HALT_CONFIRMED_A)
        self.assertNotEqual(coordinator._commands[command.command_id].status(), HaltState.HALT_CONFIRMED_ALL)

    def test_all_confirmed_only_when_b_acks(self) -> None:
        coordinator = Coordinator()
        command = coordinator.issue(
            command_id="hc-2",
            scope="ALL",
            kill_level="K1",
            reason="test",
            channel="cli",
            identity="owner",
            b_reachable=True,
        )
        coordinator.ack_a(command.command_id)
        coordinator.ack_b(command.command_id)
        self.assertEqual(coordinator._commands[command.command_id].status(), HaltState.HALT_CONFIRMED_ALL)

    def test_kill_drill_gate_requires_three_levels_and_channels(self) -> None:
        drill = Coordinator().drill
        drill.record(channel="telegram", kill_level="K1", mode="SIM")
        self.assertFalse(drill.gate_met())
        drill.record(channel="web", kill_level="K2", mode="SIM")
        drill.record(channel="cli", kill_level="K3", mode="SIM")
        self.assertFalse(drill.gate_met())
        drill.record(channel="trusted_contact", kill_level="K1", mode="SIM")
        self.assertTrue(drill.gate_met())
        with self.assertRaises(ValueError):
            drill.record(channel="web", kill_level="K1", mode="LIVE")

    def test_c1_blocks_resume_until_web_and_reprovision(self) -> None:
        mismatch = run_c1(
            KillView(
                channel="web",
                kill_level="K2",
                broker_positions=("EURUSD",),
                system_positions=(),
                fact_logged=True,
            )
        )
        self.assertFalse(mismatch.executable())
        k3 = run_c1(
            KillView(
                channel="telegram",
                kill_level="K3",
                broker_positions=(),
                system_positions=(),
                fact_logged=True,
                web_passkey=True,
                recon_clean=True,
            )
        )
        self.assertTrue(k3.executable())
        self.assertFalse(k3.resume_allowed)
        unset = run_c1(
            KillView(
                channel="web",
                kill_level="K1",
                broker_positions=(),
                system_positions=(),
                fact_logged=True,
                web_passkey=True,
                recon_clean=True,
                preflight_passed=True,
            )
        )
        self.assertFalse(unset.resume_allowed)
        self.assertIn("cool_off_unset", unset.steps)
        opened = run_c1(
            KillView(
                channel="web",
                kill_level="K1",
                broker_positions=(),
                system_positions=(),
                fact_logged=True,
                web_passkey=True,
                recon_clean=True,
                cool_off_minutes=30,
                cool_off_elapsed=True,
                preflight_passed=True,
            )
        )
        self.assertTrue(opened.resume_allowed)
        same_day = run_c1(
            KillView(
                channel="web",
                kill_level="K1",
                broker_positions=(),
                system_positions=(),
                fact_logged=True,
                web_passkey=True,
                recon_clean=True,
                cool_off_minutes=30,
                cool_off_elapsed=True,
                preflight_passed=True,
                halt_level="L3",
                killed_on="2026-10-23T00:00:00Z",
                resume_on="2026-10-23T20:00:00Z",
            )
        )
        self.assertFalse(same_day.resume_allowed)
        self.assertIn("same_day_blocked", same_day.steps)


if __name__ == "__main__":
    unittest.main()
