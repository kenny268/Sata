from __future__ import annotations

import unittest

from sate_control.kill import validate_kill, validate_resume
from sate_control.mode_badge import badge


class KillControlTests(unittest.TestCase):
    def test_default_scope_is_explicit(self) -> None:
        payload = validate_kill(scope="A", kill_level="K1", channel="cli")
        self.assertEqual(payload["scope"], "A")
        with self.assertRaises(ValueError):
            validate_kill(scope="GLOBAL", kill_level="K1", channel="cli")

    def test_resume_is_web_only(self) -> None:
        validate_resume("web")
        with self.assertRaises(ValueError):
            validate_resume("telegram")

    def test_mode_badges(self) -> None:
        self.assertEqual(badge("SIM"), ("blue", "A-SIM"))
        self.assertEqual(badge("LIVE-L1"), ("red", "A-LIVE"))


if __name__ == "__main__":
    unittest.main()
