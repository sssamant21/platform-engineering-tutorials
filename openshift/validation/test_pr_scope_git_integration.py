#!/usr/bin/env python3
"""Real-Git, offline integration checks for the OpenShift PR path-scope gate.

Requires only Python and git. Creates disposable repositories in a temporary
directory; does not access GitHub, kubeconfig, OpenShift, or production.
Run: python -m unittest openshift/validation/test_pr_scope_git_integration.py -v
"""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("check_pr_scope.py").resolve()


def git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


class RealGitScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ocp-scope-git-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.name", "Offline Test")
        git(self.root, "config", "user.email", "offline-test@example.invalid")
        (self.root / "kubernetes").mkdir()
        (self.root / "kubernetes" / "original.md").write_text("baseline\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "baseline")

    def check_scope(self):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--base", "HEAD~1"],
            cwd=self.root, capture_output=True, text=True, timeout=15,
        )

    def test_real_git_openshift_only_passes(self):
        (self.root / "openshift").mkdir()
        (self.root / "openshift" / "chapter.md").write_text("chapter\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "add OpenShift chapter")
        result = self.check_scope()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS:", result.stdout)

    def test_real_git_cross_track_rename_blocks(self):
        (self.root / "openshift").mkdir()
        git(self.root, "mv", "kubernetes/original.md", "openshift/original.md")
        git(self.root, "commit", "-qm", "move Kubernetes file into OpenShift")
        result = self.check_scope()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("kubernetes/original.md", result.stderr)

    def test_real_git_untracked_file_blocks(self):
        (self.root / "openshift").mkdir()
        (self.root / "openshift" / "chapter.md").write_text("chapter\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "add OpenShift chapter")
        (self.root / "openshift" / "untracked.md").write_text("untracked\n", encoding="utf-8")
        result = self.check_scope()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("not clean", result.stderr)


    def test_real_git_root_readme_requires_manual_review(self):
        (self.root / "README.md").write_text("navigation link\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "update navigation")
        result = self.check_scope()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("manual diff review required", result.stderr)

    def test_real_git_staged_edit_blocks(self):
        (self.root / "openshift").mkdir()
        (self.root / "openshift" / "chapter.md").write_text("chapter\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "add chapter")
        (self.root / "openshift" / "chapter.md").write_text("edited\n", encoding="utf-8")
        git(self.root, "add", ".")
        result = self.check_scope()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("not clean", result.stderr)

    def test_real_git_empty_diff_blocks(self):
        (self.root / "openshift").mkdir()
        (self.root / "openshift" / "chapter.md").write_text("chapter\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "add chapter")
        git(self.root, "commit", "--allow-empty", "-qm", "empty commit")
        result = self.check_scope()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("empty PR diff", result.stderr)


    def test_real_git_unstaged_tracked_edit_blocks(self):
        (self.root / "openshift").mkdir()
        chapter = self.root / "openshift" / "chapter.md"
        chapter.write_text("chapter\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "add chapter")
        chapter.write_text("unstaged change\n", encoding="utf-8")
        result = self.check_scope()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("not clean", result.stderr)

    def test_real_git_missing_base_ref_blocks(self):
        (self.root / "openshift").mkdir()
        (self.root / "openshift" / "chapter.md").write_text("chapter\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "add chapter")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--base", "refs/heads/does-not-exist"],
            cwd=self.root, capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("BLOCKED:", result.stderr)


    def test_real_git_newline_filename_inside_openshift_passes(self):
        # -z parsing must preserve a legal Git filename containing a newline.
        (self.root / "openshift").mkdir()
        (self.root / "openshift" / "chapter\nnotes.md").write_text("safe\\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "add newline filename in allowed path")
        result = self.check_scope()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("changed_paths=1", result.stdout)

    def test_real_git_newline_filename_outside_openshift_blocks(self):
        # A newline in a prohibited filename must not split or hide the path.
        (self.root / "kubernetes" / "unexpected\nnotes.md").write_text("unsafe\\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "change prohibited path with newline")
        result = self.check_scope()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("outside_allowlist=1", result.stdout)
        self.assertIn("BLOCKED: unexpected path", result.stderr)


if __name__ == "__main__":
    unittest.main()
