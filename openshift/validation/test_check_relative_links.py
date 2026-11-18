#!/usr/bin/env python3
"""Offline regression tests for the read-only Markdown link checker."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("check_relative_links.py")
spec = importlib.util.spec_from_file_location("check_relative_links", SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class LinkAuditTests(unittest.TestCase):
    def test_reference_definitions_before_and_after_use(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "target.md").write_text("# target\n", encoding="utf-8")
            (root / "doc.md").write_text(
                "[before][ok]\n[ok]: target.md\n[after][ok]\n",
                encoding="utf-8",
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 2)
            self.assertEqual(failures, [])

    def test_missing_reference_target_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "doc.md").write_text(
                "[broken][id]\n[id]: missing.md\n", encoding="utf-8"
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(len(failures), 1)
            self.assertIn("missing.md", failures[0])

    def test_fenced_reference_definition_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "doc.md").write_text(
                "[outside][id]\n```md\n[id]: missing.md\n```\n",
                encoding="utf-8",
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 0)
            self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
