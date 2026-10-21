"""Repository invariants for Phase 1. Standard library only."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _text_files(folder: Path, suffixes: tuple[str, ...]) -> list[Path]:
    if not folder.exists():
        return []
    return [p for p in folder.rglob("*") if p.is_file() and p.suffix in suffixes]


class RepoInvariantTests(unittest.TestCase):
    def test_group_trees_do_not_import_each_other(self) -> None:
        for path in _text_files(ROOT / "group_a", (".rs", ".py", ".toml")):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("group_b", text, str(path))
        for path in _text_files(ROOT / "group_b", (".rs", ".py", ".toml", ".md")):
            text = path.read_text(encoding="utf-8")
            # The Group B README names the rule; it must not point at A's crates.
            if path.name == "README.md":
                self.assertNotIn("sate-a-credentials", text)
                continue
            self.assertNotIn("group_a", text, str(path))

    def test_strategy_does_not_depend_on_credentials(self) -> None:
        pyproject = (ROOT / "group_a" / "strategy" / "pyproject.toml").read_text(encoding="utf-8")
        self.assertNotIn("sate-a-credentials", pyproject)
        for path in _text_files(ROOT / "group_a" / "strategy", (".py",)):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("CredentialVault", text, str(path))
            self.assertNotIn("sate_a_credentials", text, str(path))

    def test_kernel_binary_owns_the_credential_crate(self) -> None:
        cargo_path = ROOT / "group_a" / "kernel" / "kernel-a" / "Cargo.toml"
        cargo = cargo_path.read_text(encoding="utf-8")
        self.assertIn("sate-a-credentials", cargo)

    def test_deploy_workflows_are_path_scoped(self) -> None:
        workflows = ROOT / ".github" / "workflows"
        expected = {
            "deploy-group-a.yml": "group_a/**",
            "deploy-group-b.yml": "group_b/**",
            "deploy-shared.yml": "shared/**",
        }
        for name, path_filter in expected.items():
            text = (workflows / name).read_text(encoding="utf-8")
            self.assertIn(path_filter, text, name)
            self.assertNotIn("secrets.", text, name)

    def test_group_a_workflow_does_not_list_group_b_paths(self) -> None:
        text = (ROOT / ".github" / "workflows" / "deploy-group-a.yml").read_text(encoding="utf-8")
        self.assertNotIn("group_b/**", text)

    def test_intent_schema_rejects_a_combined_group(self) -> None:
        text = (ROOT / "shared" / "schemas" / "intent.schema.json").read_text(encoding="utf-8")
        self.assertIn('"A"', text)
        self.assertIn('"B"', text)
        self.assertNotIn("A+B", text)

    def test_only_kernel_binary_depends_on_credentials(self) -> None:
        allowed = {
            (ROOT / "group_a" / "kernel" / "kernel-a" / "Cargo.toml").resolve(),
            (ROOT / "group_a" / "kernel" / "credentials" / "Cargo.toml").resolve(),
        }
        for path in (ROOT / "group_a").rglob("Cargo.toml"):
            text = path.read_text(encoding="utf-8")
            if "sate-a-credentials" in text:
                self.assertIn(path.resolve(), allowed, str(path))

    def test_phase1_tracker_points_at_requirements_and_adr(self) -> None:
        import json

        tracker_path = ROOT / "shared" / "ci" / "phase-1-tracker.json"
        tracker = json.loads(tracker_path.read_text(encoding="utf-8"))
        required = (
            "adr",
            "requirements_index",
            "traceability_matrix",
            "coverage_checklist",
            "decision_log",
        )
        for key in required:
            self.assertTrue((ROOT / tracker[key]).is_file(), key)
        adr = (ROOT / tracker["adr"]).read_text(encoding="utf-8")
        self.assertIn("Accepted", adr)
        log = (ROOT / tracker["decision_log"]).read_text(encoding="utf-8")
        self.assertIn("ADR-0001", log)
        for number in range(1, 11):
            self.assertIn(f"A-DEC-{number:02d}", log)
        for number in range(1, 7):
            self.assertIn(f"OI-TG-{number:02d}", log)

    def test_compose_is_a_control_plane_without_secrets(self) -> None:
        text = (ROOT / "group_a" / "infra" / "compose.yaml").read_text(encoding="utf-8")
        self.assertIn("sate-a-control", text)
        self.assertNotIn("password", text.lower())
        self.assertNotIn("ports:", text)
        self.assertNotIn("group_b", text)

    def test_group_a_workflow_lints_scans_and_versions(self) -> None:
        text = (ROOT / ".github" / "workflows" / "deploy-group-a.yml").read_text(encoding="utf-8")
        for needle in ("clippy", "cargo audit", "upload-artifact", "ruff"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
