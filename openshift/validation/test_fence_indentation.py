"""Regression: four-space-indented backticks are code, not a Markdown fence.

Offline-only; no OpenShift cluster, credentials or network required.
"""
import tempfile
import unittest
from pathlib import Path

from check_relative_links import audit


class IndentedFenceRegression(unittest.TestCase):
    def test_four_space_indented_fence_does_not_hide_real_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "example.md").write_text(
                "    ```\n[missing](not-present.md)\n    ```\n",
                encoding="utf-8",
            )
            checked, failures = audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(len(failures), 1)

    def test_three_space_fence_hides_example_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "example.md").write_text(
                "   ```md\n[example](not-present.md)\n   ```\n",
                encoding="utf-8",
            )
            checked, failures = audit(root)
            self.assertEqual(checked, 0)
            self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
