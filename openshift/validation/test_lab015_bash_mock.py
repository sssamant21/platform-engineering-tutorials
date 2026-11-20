"""Isolated Bash execution tests for Lab 015 using a fake oc executable.

No cluster, credentials, network or actual oc binary required. Run from repo root:
python -m unittest discover -s openshift/validation -p 'test_lab015_bash_mock.py' -v
Requires bash and Python 3; skip on hosts without bash.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

LAB = Path(__file__).resolve().parents[1] / "labs" / "015-recovery-read-only-readiness-audit.md"
MOCK_OC = r'''#!/usr/bin/env python3
import os, sys
from pathlib import Path
args = sys.argv[1:]
with Path(os.environ["OC_TRACE"]).open("a", encoding="utf-8") as out:
    out.write(" ".join(args) + "\n")
scenario = os.environ.get("OC_SCENARIO", "ok")
if args == ["whoami"]:
    if scenario == "identity_fail": sys.exit(7)
    print("mock-user")
elif args == ["config", "current-context"]:
    print("mock-context")
elif args[:3] == ["config", "view", "--minify"]:
    print("https://wrong.example.invalid" if scenario == "mismatch" else "https://approved.example.invalid")
elif args == ["version"]:
    print("mock version")
elif args[:2] == ["auth", "can-i"]:
    if scenario == "auth_fail": sys.exit(9)
    print("no" if scenario == "denied" else "yes")
elif args and args[0] == "get":
    if scenario == "read_fail": sys.exit(11)
else:
    sys.exit(98)
'''

@unittest.skipUnless(shutil.which("bash"), "bash is not installed")
class Lab015BashMock(unittest.TestCase):
    def run_case(self, scenario):
        source = LAB.read_text(encoding="utf-8")
        match = re.search(r"```bash\n(.*?)\n```", source, re.S)
        self.assertIsNotNone(match)
        with tempfile.TemporaryDirectory(prefix="oc015-mock-") as directory:
            root = Path(directory)
            mock = root / "oc"
            mock.write_text(MOCK_OC, encoding="utf-8")
            mock.chmod(0o700)
            trace = root / "trace.txt"
            env = os.environ.copy()
            env.update({
                "PATH": str(root) + os.pathsep + env.get("PATH", ""),
                "EXPECTED_API_SERVER": "https://approved.example.invalid",
                "OC_SCENARIO": scenario,
                "OC_TRACE": str(trace),
            })
            result = subprocess.run(["bash", "-c", match.group(1)], cwd=root,
                                    env=env, capture_output=True, text=True, timeout=15)
            commands = trace.read_text(encoding="utf-8").splitlines() if trace.exists() else []
            return result, commands

    def test_success_four_authorizations_and_reads(self):
        result, commands = self.run_case("ok")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sum(x.startswith("auth can-i ") for x in commands), 4)
        self.assertEqual(sum(x.startswith("get ") for x in commands), 4)

    def test_identity_failure_stops_before_resource_access(self):
        result, commands = self.run_case("identity_fail")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(commands, ["whoami"])

    def test_server_mismatch_stops_before_version_and_reads(self):
        result, commands = self.run_case("mismatch")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(x == "version" or x.startswith("auth ") or x.startswith("get ") for x in commands))

    def test_denial_skips_all_resource_reads(self):
        result, commands = self.run_case("denied")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(sum(x.startswith("auth can-i ") for x in commands), 4)
        self.assertFalse(any(x.startswith("get ") for x in commands))
        self.assertEqual(result.stdout.count("SKIP:"), 4)

    def test_authorization_error_marks_incomplete(self):
        result, commands = self.run_case("auth_fail")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sum(x.startswith("auth can-i ") for x in commands), 4)
        self.assertFalse(any(x.startswith("get ") for x in commands))
        self.assertIn("INCOMPLETE", result.stderr)

    def test_read_error_marks_incomplete(self):
        result, commands = self.run_case("read_fail")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sum(x.startswith("get ") for x in commands), 4)
        self.assertIn("INCOMPLETE", result.stderr)

if __name__ == "__main__":
    unittest.main()
