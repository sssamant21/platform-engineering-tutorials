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
if any(os.environ.get(name) for name in ("KUBECONFIG", "AWS_SECRET_ACCESS_KEY", "AZURE_CLIENT_SECRET")):
    sys.exit(97)
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
    if scenario == "version_fail": sys.exit(13)
    print("mock version")
elif args[:2] == ["auth", "can-i"]:
    if scenario == "auth_fail": sys.exit(9)
    print("no" if scenario == "denied" else "yes")
elif args and args[0] == "get":
    if scenario == "read_fail": sys.exit(11)
    print("SENTINEL_CLUSTER_RESOURCE_PAYLOAD_DO_NOT_EMIT")
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
            env = {
                "PATH": str(root) + os.pathsep + os.defpath,
                "HOME": str(root),
                "TMPDIR": str(root),
                "PYTHONNOUSERSITE": "1",
            }
            env.update({
                "EXPECTED_API_SERVER": "https://approved.example.invalid",
                "OC_SCENARIO": scenario,
                "OC_TRACE": str(trace),
            })
            result = subprocess.run(["bash", "-c", match.group(1)], cwd=root,
                                    env=env, capture_output=True, text=True, timeout=15)
            commands = trace.read_text(encoding="utf-8").splitlines() if trace.exists() else []
            return result, commands

    def test_success_five_authorizations_and_reads(self):
        result, commands = self.run_case("ok")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sum(x.startswith("auth can-i ") for x in commands), 5)
        self.assertEqual(sum(x.startswith("get ") for x in commands), 5)

    def test_success_does_not_emit_resource_payloads(self):
        """A successful read-only audit must not print fetched cluster resources."""
        result, commands = self.run_case("ok")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sum(x.startswith("get ") for x in commands), 5)
        self.assertNotIn("mock-user", result.stdout)
        self.assertNotIn("mock-context", result.stdout)
        self.assertNotIn("mock version", result.stdout)
        self.assertNotIn("SENTINEL_CLUSTER_RESOURCE_PAYLOAD_DO_NOT_EMIT", result.stdout)
        self.assertNotIn("SENTINEL_CLUSTER_RESOURCE_PAYLOAD_DO_NOT_EMIT", result.stderr)
        self.assertIn("Read-only checks completed", result.stdout)

    def test_success_uses_only_approved_read_only_commands(self):
        """Catch accidental introduction of mutating commands into the lab."""
        result, commands = self.run_case("ok")
        self.assertEqual(result.returncode, 0, result.stderr)
        # Pin the exact audited command inventory; broad prefixes hide unsafe reads.
        allowed = {
            "whoami", "config current-context",
            "config view --minify -o jsonpath={.clusters[0].cluster.server}",
            "version",
            "auth can-i get clusterversions.config.openshift.io --resource-name=version",
            "auth can-i list clusteroperators.config.openshift.io",
            "auth can-i list nodes",
            "auth can-i list machineconfigpools.machineconfiguration.openshift.io",
            "auth can-i get infrastructures.config.openshift.io --resource-name=cluster",
            "get clusterversion version", "get clusteroperators",
            "get nodes -l node-role.kubernetes.io/master",
            "get machineconfigpools", "get infrastructure cluster",
        }
        self.assertEqual(len(commands), 14, commands)
        self.assertEqual(set(commands), allowed, commands)
        self.assertEqual(len(set(commands)), len(commands), "Repeated oc invocation")

    def test_identity_failure_stops_before_resource_access(self):
        result, commands = self.run_case("identity_fail")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(commands, ["whoami"])

    def test_server_mismatch_stops_before_version_and_reads(self):
        result, commands = self.run_case("mismatch")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(x == "version" or x.startswith("auth ") or x.startswith("get ") for x in commands))

    def test_version_failure_stops_before_authorization_and_reads(self):
        result, commands = self.run_case("version_fail")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(commands.count("version"), 1)
        self.assertFalse(any(x.startswith("auth ") or x.startswith("get ") for x in commands))
        self.assertIn("STOP: version lookup failed", result.stderr)

    def test_denial_skips_all_resource_reads(self):
        result, commands = self.run_case("denied")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(sum(x.startswith("auth can-i ") for x in commands), 5)
        self.assertFalse(any(x.startswith("get ") for x in commands))
        self.assertEqual(result.stdout.count("SKIP:"), 5)

    def test_authorization_error_marks_incomplete(self):
        result, commands = self.run_case("auth_fail")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sum(x.startswith("auth can-i ") for x in commands), 5)
        self.assertFalse(any(x.startswith("get ") for x in commands))
        self.assertIn("INCOMPLETE", result.stderr)

    def test_read_error_marks_incomplete(self):
        result, commands = self.run_case("read_fail")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sum(x.startswith("get ") for x in commands), 5)
        self.assertIn("INCOMPLETE", result.stderr)


    def test_parent_credentials_not_inherited_by_mock(self):
        """A credential-like parent variable must not reach the fake oc process."""
        from unittest.mock import patch
        with patch.dict(os.environ, {
            "KUBECONFIG": "/nonexistent/private-kubeconfig",
            "AWS_SECRET_ACCESS_KEY": "sentinel-not-a-real-secret",
            "AZURE_CLIENT_SECRET": "sentinel-not-a-real-secret",
            "OC_TRACE": "/nonexistent/parent-trace",
        }):
            result, commands = self.run_case("ok")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sum(x.startswith("get ") for x in commands), 5)

if __name__ == "__main__":
    unittest.main()
