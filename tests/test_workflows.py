from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_workflows.py"
SPEC = importlib.util.spec_from_file_location("validate_workflows", MODULE_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class WorkflowRepositoryTest(unittest.TestCase):
    def test_workflows_pass_validation(self) -> None:
        self.assertEqual([], VALIDATOR.validate_repository())

    def test_manifest_totals_match_workflows(self) -> None:
        manifest = json.loads((ROOT / "workflow-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(7, manifest["workflow_count"])
        self.assertEqual(315, manifest["functional_node_count"])
        self.assertEqual(336, manifest["connection_edge_count"])
        self.assertEqual(315, sum(item["nodes"] for item in manifest["workflows"]))
        self.assertEqual(336, sum(item["edges"] for item in manifest["workflows"]))

    def test_all_repository_json_is_valid(self) -> None:
        json_files = sorted(ROOT.rglob("*.json"))
        self.assertEqual(12, len(json_files))
        for path in json_files:
            with self.subTest(path=path.relative_to(ROOT)):
                json.loads(path.read_text(encoding="utf-8"))

    def test_every_configuration_marker_is_documented(self) -> None:
        workflow_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((ROOT / "workflows").glob("*.json"))
        )
        markers = set(re.findall(r"\b(?:YOUR|SELECT)_[A-Z0-9_]+\b", workflow_text))
        setup = (ROOT / "docs" / "SETUP.md").read_text(encoding="utf-8")
        self.assertEqual(13, len(markers))
        self.assertEqual([], sorted(marker for marker in markers if marker not in setup))

    def test_relative_markdown_links_resolve(self) -> None:
        missing: list[str] = []
        for path in ROOT.rglob("*.md"):
            content = path.read_text(encoding="utf-8")
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", content):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                relative_target = target.split("#", 1)[0]
                if relative_target and not (path.parent / relative_target).resolve().exists():
                    missing.append(f"{path.relative_to(ROOT)} -> {target}")
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
