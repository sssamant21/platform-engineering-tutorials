#!/usr/bin/env python3
"""Offline PowerShell parity checks for the committed Chapter 015 lab.

Run: python -m unittest discover -s openshift/tests -p 'test_ch015_powershell_mock.py' -v
Requires pwsh; tests skip otherwise. No actual oc binary or cluster is used.
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parents[1] / "labs/015-recovery-read-only-readiness-audit.md"
BLOCK = re.compile(r"## Procedure — Windows PowerShell\s*```powershell\n(.*?)\n```", re.S)
# Function shadows any executable named oc; a controlled PATH and empty HOME
# prevent accidental resolution of a real oc binary.
MOCK = r'''
$script:Calls = [System.Collections.Generic.List[string]]::new()
function oc {
  $argsText = ($args -join ' ')
  $script:Calls.Add($argsText)
  $global:LASTEXITCODE = 0
  if ($argsText -eq 'whoami') { return 'mock-user' }
  if ($argsText -eq 'config current-context') { return 'mock-context' }
  if ($argsText -like 'config view --minify*') { return $env:MOCK_SERVER }
  if ($argsText -eq 'version') { return 'mock-version' }
  if ($argsText -like 'auth can-i *') {
    if ($env:MOCK_DENY -eq 'all' -or ($env:MOCK_DENY -and $argsText.Contains($env:MOCK_DENY))) {
      $global:LASTEXITCODE = [int]$env:MOCK_AUTH_EXIT
      return $env:MOCK_AUTH_ANSWER
    }
    return 'yes'
  }
  if ($argsText -like 'get *') {
    if ($env:MOCK_FAIL_READ -and $argsText.Contains($env:MOCK_FAIL_READ)) {
      $global:LASTEXITCODE = 11
      return
    }
    return 'synthetic-resource'
  }
  throw "Unexpected oc invocation: $argsText"
}
'''
@unittest.skipUnless(shutil.which("pwsh"), "PowerShell 7 (pwsh) unavailable")
class Lab015PowerShellMock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        match = BLOCK.search(LAB.read_text(encoding="utf-8"))
        if not match:
            raise AssertionError("Committed PowerShell block not found")
        cls.procedure = match.group(1)

    def run_case(self, **overrides):
        with tempfile.TemporaryDirectory(prefix="ch015-ps-") as tmp:
            directory = Path(tmp)
            trace = directory / "trace.txt"
            script = directory / "test.ps1"
            # finally records calls even when the procedure throws.
            script.write_text(
                MOCK + "\ntry {\n" + self.procedure +
                "\n} finally { $script:Calls | Set-Content -LiteralPath '" +
                str(trace).replace("'", "''") + "' }\n",
                encoding="utf-8",
            )
            env = {
                "PATH": str(directory) + os.pathsep + os.defpath,
                "HOME": str(directory),
                "TMPDIR": str(directory),
                "XDG_CONFIG_HOME": str(directory),
                "POWERSHELL_TELEMETRY_OPTOUT": "1",
                "POWERSHELL_UPDATECHECK": "Off",
                "EXPECTED_API_SERVER": "https://approved.invalid:6443",
                "MOCK_SERVER": "https://approved.invalid:6443",
                "MOCK_AUTH_ANSWER": "no",
                "MOCK_AUTH_EXIT": "0",
                "MOCK_DENY": "",
                "MOCK_FAIL_READ": "",
            }
            env.update(overrides)
            # The lab references a PowerShell variable, not an environment variable.
            bootstrap = "$ExpectedApiServer = $env:EXPECTED_API_SERVER\n"
            script.write_text(bootstrap + script.read_text(encoding="utf-8"), encoding="utf-8")
            result = subprocess.run(
                [shutil.which("pwsh"), "-NoLogo", "-NoProfile", "-NonInteractive",
                 "-File", str(script)], cwd=directory, env=env,
                capture_output=True, text=True, timeout=20, check=False,
            )
            calls = trace.read_text(encoding="utf-8").splitlines() if trace.exists() else []
            self.assertTrue(all(x.startswith(("whoami", "config ", "version", "auth can-i ", "get ")) for x in calls), calls)
            return result, calls

    def test_all_authorized(self):
        result, calls = self.run_case()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sum(x.startswith("auth can-i ") for x in calls), 5)
        self.assertEqual(sum(x.startswith("get ") for x in calls), 5)

    def test_server_mismatch_blocks_reads(self):
        result, calls = self.run_case(MOCK_SERVER="https://wrong.invalid:6443")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(x.startswith(("auth can-i ", "get ")) for x in calls))

    def test_missing_approved_server_blocks_reads(self):
        result, calls = self.run_case(EXPECTED_API_SERVER="")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(x.startswith(("auth can-i ", "get ")) for x in calls))

    def test_all_denied_skips_reads(self):
        result, calls = self.run_case(MOCK_DENY="all")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sum(x.startswith("auth can-i ") for x in calls), 5)
        self.assertFalse(any(x.startswith("get ") for x in calls))

    def test_mcp_read_failure_is_incomplete(self):
        result, calls = self.run_case(MOCK_FAIL_READ="machineconfigpools")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any(x.startswith("get machineconfigpools") for x in calls))

    def test_nonzero_authorization_with_yes_fails_closed(self):
        result, calls = self.run_case(
            MOCK_DENY="machineconfigpools", MOCK_AUTH_ANSWER="yes", MOCK_AUTH_EXIT="7"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(x.startswith("get machineconfigpools") for x in calls))

    def test_denied_mcp_skips_only_mcp_read(self):
        result, calls = self.run_case(
            MOCK_DENY="machineconfigpools", MOCK_AUTH_ANSWER="no", MOCK_AUTH_EXIT="0"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sum(x.startswith("auth can-i ") for x in calls), 5)
        self.assertEqual(sum(x.startswith("get ") for x in calls), 4)
        self.assertFalse(any(x.startswith("get machineconfigpools") for x in calls))

if __name__ == "__main__":
    unittest.main()
