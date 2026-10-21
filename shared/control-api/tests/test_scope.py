import unittest

from sate_control.scope import require_scope


class ScopeTests(unittest.TestCase):
    def test_accepts_one_group(self) -> None:
        self.assertEqual(require_scope("A"), "A")
        self.assertEqual(require_scope("B"), "B")

    def test_rejects_combined_or_global(self) -> None:
        for bad in ("GLOBAL", "A+B", "ALL", ""):
            with self.assertRaises(ValueError):
                require_scope(bad)


if __name__ == "__main__":
    unittest.main()
