#!/usr/bin/env python3
"""Offline unit tests for the OpenShift PR path-scope gate.

Mocks git output: never invokes git, oc, a network endpoint, or a cluster.
Run: python -m unittest discover -s openshift/validation -p 'test_*.py' -v
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).with_name("check_pr_scope.py")
SPEC = importlib.util.spec_from_file_location("check_pr_scope", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ScopeGateTests(unittest.TestCase):
    def check(self, paths, *, error=None):
        def fake_git(*args):
            if error and args[0] == "diff":
                raise RuntimeError(error)
            if args[:2] == ("rev-parse", "--show-toplevel"):
                return b"/tmp/safe-checkout\n"
            if args[:2] == ("rev-parse", "--show-prefix"):
                return b""
            if args[0] == "diff":
                return b"".join(p.encode() + b"\0" for p in paths)
            return b"fake-sha\n"

        with patch.object(MODULE, "run_git", side_effect=fake_git), patch.object(sys, "argv", ["check_pr_scope.py"]), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return MODULE.main()

    def test_openshift_only_passes(self):
        self.assertEqual(self.check(["openshift/MASTER-PLAN.md", "openshift/validation/check_pr_scope.py"]), 0)

    def test_kubernetes_change_fails(self):
        self.assertEqual(self.check(["openshift/README.md", "kubernetes/README.md"]), 1)

    def test_other_repository_path_fails(self):
        self.assertEqual(self.check(["data-platform-engineering-tutorials/README.md"]), 1)

    def test_root_readme_requires_manual_review(self):
        self.assertEqual(self.check(["openshift/README.md", "README.md"]), 2)

    def test_empty_diff_blocks(self):
        self.assertEqual(self.check([]), 2)

    def test_git_failure_blocks(self):
        self.assertEqual(self.check(["openshift/README.md"], error="missing base ref"), 2)


if __name__ == "__main__":
    unittest.main()
