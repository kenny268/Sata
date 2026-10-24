from __future__ import annotations

import unittest

from sate_control.passkey import PasskeyInvalid, PasskeyRequired, require_passkey


class PasskeyTests(unittest.TestCase):
    def test_missing_assertion_is_rejected(self) -> None:
        with self.assertRaises(PasskeyRequired):
            require_passkey(assertion=None, action="resume")

    def test_short_assertion_is_rejected(self) -> None:
        with self.assertRaises(PasskeyInvalid):
            require_passkey(assertion="short", action="resume")

    def test_base64url_assertion_is_accepted(self) -> None:
        token = "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGWFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHk"
        self.assertEqual(require_passkey(assertion=token, action="resume"), token)


if __name__ == "__main__":
    unittest.main()
