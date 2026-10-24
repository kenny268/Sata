from __future__ import annotations

import unittest

from sate_notifier.replay import ReplayGuard


class ReplayTests(unittest.TestCase):
    def test_duplicate_update_is_rejected(self) -> None:
        guard = ReplayGuard()
        self.assertTrue(guard.accept(1))
        self.assertFalse(guard.accept(1))


if __name__ == "__main__":
    unittest.main()
