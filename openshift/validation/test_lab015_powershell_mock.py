"""Offline PowerShell mock execution for Lab 015; no real oc or cluster access.

Run: python -m unittest discover -s openshift/validation -p 'test_lab015_powershell_mock.py' -v
Requires pwsh (PowerShell 7). Skips if unavailable; Windows PowerShell 5.1 is not
covered by this suite and needs separate validation.
"""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

LAB = Path(__file__).resolve().parents[1] / "labs" / "015-recovery-read-only-readiness-audit.md"
PWSH = shutil.which("pwsh")

MOCK = r"""
$ExpectedApiServer = 'https://approved.example.invalid'
$script:Scenario = $env:OC_SCENARIO
$script:Trace = $env:OC_TRACE
function global:oc {
  if ($env:KUBECONFIG -or $env:AWS_SECRET_ACCESS_KEY -or $env:AZURE_CLIENT_SECRET) { $global:LASTEXITCODE = 97; throw 'Mock credential inheritance detected' }
  $a = @($args | ForEach-Object { [string]$_ })
  [System.IO.File]::AppendAllText($script:Trace, (($a -join ' ') + [Environment]::NewLine))
  $global:LASTEXITCODE = 0
  if ($a.Count -eq 1 -and $a[0] -eq 'whoami') {
    if ($script:Scenario -eq 'identity_fail') { $global:LASTEXITCODE = 7; return }
    return 'mock-user'
  }
  if (($a -join ' ') -eq 'config current-context') { return 'mock-context' }
  if ($a.Count -ge 3 -and ($a[0..2] -join ' ') -eq 'config view --minify') {
    if ($script:Scenario -eq 'mismatch') { return 'https://wrong.example.invalid' }
    return 'https://approved.example.invalid'
  }
  if (($a -join ' ') -eq 'version') {
    if ($script:Scenario -eq 'version_fail') { $global:LASTEXITCODE = 13; return }
    return 'mock-version'
  }
  if ($a.Count -ge 2 -and ($a[0..1] -join ' ') -eq 'auth can-i') {
    if ($script:Scenario -eq 'auth_fail') { $global:LASTEXITCODE = 9; return }
    if ($script:Scenario -eq 'denied') { return 'no' }
    return 'yes'
  }
  if ($a.Count -gt 0 -and $a[0] -eq 'get') {
    if ($script:Scenario -eq 'read_fail') { $global:LASTEXITCODE = 11 }
    return
  }
  $global:LASTEXITCODE = 98
}
"""
@unittest.skipUnless(PWSH, "PowerShell 7 (pwsh) not installed")
class Lab015PowerShellMock(unittest.TestCase):
    def run_case(self, scenario, inject_parent_secrets=False):
        source = LAB.read_text(encoding="utf-8")
        match = re.search(r"```powershell\n(.*?)\n```", source, re.S)
        self.assertIsNotNone(match, "PowerShell lab code fence missing")
        with tempfile.TemporaryDirectory(prefix="oc015-ps-") as directory:
            root = Path(directory)
            trace = root / "trace.txt"
            script = root / "mock.ps1"
            script.write_text(MOCK + "\n" + match.group(1), encoding="utf-8")
            import os
            env = {
                "PATH": os.environ.get("PATH", os.defpath),
                "HOME": str(root),
                "USERPROFILE": str(root),
                "TMPDIR": str(root),
                "TEMP": str(root),
                "TMP": str(root),
                "XDG_CONFIG_HOME": str(root),
                "OC_SCENARIO": scenario,
                "OC_TRACE": str(trace),
            }
            if inject_parent_secrets:
                from unittest.mock import patch.dict
                with patch.dict(os.environ, {
                    'KUBECONFIG': '/synthetic/never-use-kubeconfig',
                    'AWS_SECRET_ACCESS_KEY': 'synthetic-test-value',
                    'AZURE_CLIENT_SECRET': 'synthetic-test-value',
                }):
                    # The explicit subprocess env must remain free of parent secrets.
                    result = subprocess.run([PWSH, '-NoLogo', '-NoProfile', '-NonInteractive',
                                             '-File', str(script)], cwd=root, env=env,
                                            capture_output=True, text=True, timeout=20)
            else:
                result = subprocess.run([PWSH, "-NoLogo", "-NoProfile", "-NonInteractive",
                                     "-File", str(script)], cwd=root, env=env,
                                    capture_output=True, text=True, timeout=20)
            commands = trace.read_text(encoding="utf-8").splitlines() if trace.exists() else []
            return result, commands

    def test_success_four_authorizations_and_reads(self):
        result, commands = self.run_case("ok")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sum(x.startswith("auth can-i ") for x in commands), 4)
        self.assertEqual(sum(x.startswith("get ") for x in commands), 4)

    def test_parent_credentials_are_not_inherited(self):
        result, commands = self.run_case('ok', inject_parent_secrets=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sum(x.startswith('get ') for x in commands), 4)
        self.assertNotIn('Mock credential inheritance detected', result.stderr)

    def test_identity_failure_stops(self):
        result, commands = self.run_case("identity_fail")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(commands, ["whoami"])

    def test_server_mismatch_stops_before_reads(self):
        result, commands = self.run_case("mismatch")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(x == "version" or x.startswith("auth ") or x.startswith("get ") for x in commands))

    def test_version_failure_stops_before_authorization_and_reads(self):
        result, commands = self.run_case("version_fail")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(commands.count("version"), 1)
        self.assertFalse(any(x.startswith("auth ") or x.startswith("get ") for x in commands))
        self.assertIn("STOP: version lookup failed", result.stderr)

    def test_denied_skips_reads(self):
        result, commands = self.run_case("denied")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sum(x.startswith("auth can-i ") for x in commands), 4)
        self.assertFalse(any(x.startswith("get ") for x in commands))
        self.assertEqual(result.stdout.count("SKIP:"), 4)

    def test_authorization_error_is_incomplete(self):
        result, commands = self.run_case("auth_fail")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(x.startswith("get ") for x in commands))
        self.assertIn("INCOMPLETE", result.stderr)

    def test_resource_read_error_is_incomplete(self):
        result, commands = self.run_case("read_fail")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sum(x.startswith("get ") for x in commands), 4)
        self.assertIn("INCOMPLETE", result.stderr)

if __name__ == "__main__":
    unittest.main()
