#!/usr/bin/env python3
"""Offline Bash acceptance tests for committed Lab 015.

Run from repository root:
  python -m unittest discover -s openshift/tests -p 'test_ch015_bash_mock.py' -v

No live oc binary, kubeconfig, credentials, or network access is used.
PowerShell parity is NOT established by this suite.
"""
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "openshift/labs/015-recovery-read-only-readiness-audit.md"
BASH = re.compile(r"## Procedure — Linux/macOS \(Bash\)\s*```bash\n(.*?)\n```", re.S)
MOCK = """#!/usr/bin/env python3
import os, sys
from pathlib import Path
args = sys.argv[1:]
with Path(os.environ["MOCK_LOG"]).open("a", encoding="utf-8") as f:
    f.write(" ".join(args) + "\\n")
if args == ["whoami"]: print("synthetic-user"); sys.exit(0)
if args == ["config", "current-context"]: print("synthetic-context"); sys.exit(0)
if args[:3] == ["config", "view", "--minify"]:
    print(os.environ.get("MOCK_SERVER", "https://approved.invalid:6443")); sys.exit(0)
if args == ["version"]: print("synthetic version"); sys.exit(0)
if args[:2] == ["auth", "can-i"]:
    key = " ".join(args[2:])
    if os.environ.get("MOCK_DENY", "") in key and os.environ.get("MOCK_DENY"):
        print(os.environ.get("MOCK_AUTH_ANSWER", "no"))
        sys.exit(int(os.environ.get("MOCK_AUTH_EXIT", "0")))
    print("yes"); sys.exit(0)
if args and args[0] == "get":
    if os.environ.get("MOCK_FAIL_READ", "") in " ".join(args) and os.environ.get("MOCK_FAIL_READ"):
        print("synthetic Forbidden", file=sys.stderr); sys.exit(1)
    print("synthetic read"); sys.exit(0)
print("unexpected mock invocation", file=sys.stderr); sys.exit(99)
"""

class Lab015BashMock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        text = LAB.read_text(encoding="utf-8")
        match = BASH.search(text)
        if not match:
            raise AssertionError("Cannot extract committed Bash procedure")
        cls.script = match.group(1)
        forbidden = ("cluster-backup.sh", "cluster-restore.sh", "oc config view --raw")
        for command in forbidden:
            if re.search(r"^\s*" + re.escape(command), cls.script, re.M):
                raise AssertionError("Unsafe command in lab")

    def run_case(self, **settings):
        with tempfile.TemporaryDirectory(prefix="oc-ch015-mock-") as tmp:
            path = Path(tmp)
            oc = path / "oc"
            oc.write_text(MOCK, encoding="utf-8")
            oc.chmod(0o700)
            log = path / "calls.log"
            env = {
                "PATH": str(path) + os.pathsep + os.environ.get("PATH", ""),
                "EXPECTED_API_SERVER": "https://approved.invalid:6443",
                "MOCK_LOG": str(log),
                "MOCK_SERVER": "https://approved.invalid:6443",
            }
            env.update(settings)
            # Execute only the Bash fenced block extracted from the committed Markdown.
            result = subprocess.run(
                ["bash", "--noprofile", "--norc", "-c", self.script],
                env=env, text=True, capture_output=True, timeout=15, check=False
            )
            calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
            self.assertTrue(all(
                line.startswith(("whoami", "config ", "version", "auth can-i ", "get "))
                for line in calls
            ), calls)
            return result, calls

    def test_m01_all_authorized(self):
        result, calls = self.run_case()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sum(x.startswith("auth can-i ") for x in calls), 5)
        self.assertEqual(sum(x.startswith("get ") for x in calls), 5)

    def test_m02_wrong_api_identity_stops_before_reads(self):
        result, calls = self.run_case(MOCK_SERVER="https://other.invalid:6443")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(x.startswith(("auth can-i ", "get ")) for x in calls))

    def test_m05_denied_mcp_skips_read(self):
        result, calls = self.run_case(MOCK_DENY="machineconfigpools")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SKIP: MachineConfigPools", result.stdout)
        self.assertNotIn("get machineconfigpools", calls)

    def test_m08_nonzero_yes_fails_closed(self):
        result, calls = self.run_case(
            MOCK_DENY="machineconfigpools", MOCK_AUTH_ANSWER="yes", MOCK_AUTH_EXIT="1"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("get machineconfigpools", calls)

    def test_m10_resource_read_failure(self):
        result, calls = self.run_case(MOCK_FAIL_READ="machineconfigpools")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("get machineconfigpools", calls)

if __name__ == "__main__":
    unittest.main()
