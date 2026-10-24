"""SEC: cognitive plane must not import broker/kernel order paths."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "sate_cognitive"
_FORBIDDEN_PREFIXES = (
    "sate_mt5_bridge",
    "sate_runtime",
    "sate_strategy_a",
)


class CognitiveSecurityTests(unittest.TestCase):
    def test_no_order_path_imports(self) -> None:
        for path in sorted(PKG.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertFalse(
                            any(alias.name.startswith(p) for p in _FORBIDDEN_PREFIXES),
                            f"{path.name} imports {alias.name}",
                        )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    self.assertFalse(
                        any(node.module.startswith(p) for p in _FORBIDDEN_PREFIXES),
                        f"{path.name} imports from {node.module}",
                    )


if __name__ == "__main__":
    unittest.main()
