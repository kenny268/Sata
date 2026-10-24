from __future__ import annotations

import unittest

from sate_notifier.alive import handle_alive


class AliveTests(unittest.TestCase):
    def test_alive_is_reduce_only_presence(self) -> None:
        result = handle_alive(chat_allowed=True, user_allowed=True)
        self.assertEqual(result["risk_increasing"], "false")
        self.assertEqual(result["channel"], "telegram_alive")

    def test_allowlist_is_required(self) -> None:
        with self.assertRaises(PermissionError):
            handle_alive(chat_allowed=False, user_allowed=True)


if __name__ == "__main__":
    unittest.main()
