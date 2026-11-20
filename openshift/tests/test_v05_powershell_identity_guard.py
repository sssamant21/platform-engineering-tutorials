"""Offline PowerShell identity-guard regression tests. No real oc executable is used.

Requires Python 3 and PowerShell 7 (pwsh). Extracts the PowerShell snippet
verbatim from the V04 worksheet. Uses a session-local PowerShell function
named oc, so PATH cannot accidentally resolve a real cluster client.
"""
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKSHEET = ROOT / "validation" / "V04-upgrade-etcd-recovery-evidence-worksheet.md"
START = "```powershell"
END = "```"


def extract_script():
    text = WORKSHEET.read_text(encoding="utf-8")
    assert text.count(START) == 1, "Expected exactly one V04 PowerShell block"
    return text.split(START, 1)[1].split(END, 1)[0].strip()


MOCK = r"""
function oc {
  $argvText = ($args -join ' ')
  Add-Content -LiteralPath $env:MOCK_LOG -Value $argvText
  $global:LASTEXITCODE = 0
  if ($argvText -eq 'whoami') {
    if ($env:MOCK_FAILURE -eq 'whoami') { $global:LASTEXITCODE = 1; return }
    'mock-user'; return
  }
  if ($argvText -eq 'config current-context') {
    if ($env:MOCK_FAILURE -eq 'context') { $global:LASTEXITCODE = 1; return }
    if ($env:MOCK_FAILURE -eq 'wrong-context') { 'unexpected'; return }
    'isolated-test'; return
  }
  if ($argvText -like 'config view --minify *') {
    if ($env:MOCK_FAILURE -eq 'server') { $global:LASTEXITCODE = 1; return }
    if ($env:MOCK_FAILURE -eq 'wrong-server') { 'https://wrong.invalid:6443'; return }
    'https://api.test.invalid:6443'; return
  }
  if ($argvText -eq 'version') {
    if ($env:MOCK_FAILURE -eq 'version') { $global:LASTEXITCODE = 1; return }
    'mock-version'; return
  }
  if ($argvText -like 'auth can-i *') {
    if ($env:MOCK_FAILURE -eq 'deny') { 'no'; return }
    if ($env:MOCK_FAILURE -eq 'auth-error') { $global:LASTEXITCODE = 1; return }
    if ($env:MOCK_FAILURE -eq 'ambiguous-auth') { 'maybe'; return }
    'yes'; return
  }
  if ($argvText -like 'get *') {
    if ($env:MOCK_FAILURE -eq 'read') { $global:LASTEXITCODE = 1; return }
    'mock-resource'; return
  }
  throw "Unexpected mock oc invocation: $argvText"
}
"""


@unittest.skipUnless(shutil.which("pwsh"), "PowerShell 7 not installed")
class PowerShellIdentityGuardTests(unittest.TestCase):
    def run_case(self, failure="", expected_context="isolated-test",
                 expected_server="https://api.test.invalid:6443"):
        with tempfile.TemporaryDirectory() as tmp:
            log = pathlib.Path(tmp) / "calls.log"
            script = pathlib.Path(tmp) / "run.ps1"
            script.write_text(
                "$ErrorActionPreference = 'Stop'\n" + MOCK +
                "\ntry {\n" + extract_script() +
                "\n} catch { [Console]::Error.WriteLine($_.Exception.Message); exit 1 }\n",
                encoding="utf-8",
            )
            env = dict(os.environ)
            env.update(MOCK_LOG=str(log), MOCK_FAILURE=failure,
                       EXPECTED_CONTEXT=expected_context,
                       EXPECTED_SERVER=expected_server)
            # No real kubeconfig is supplied to the mock session.
            env["KUBECONFIG"] = str(pathlib.Path(tmp) / "nonexistent-kubeconfig")
            proc = subprocess.run(
                ["pwsh", "-NoLogo", "-NoProfile", "-NonInteractive",
                 "-File", str(script)],
                env=env, capture_output=True, text=True, timeout=30,
            )
            calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
            # Strict allowlist: unexpected verbs must fail even when not in a
            # short denylist. All calls are intercepted by the session mock.
            allowed = {
                "whoami",
                "config current-context",
                "config view --minify -o jsonpath={.clusters[0].cluster.server}",
                "version",
                "auth can-i get clusterversions.config.openshift.io --resource-name=version",
                "auth can-i list clusteroperators.config.openshift.io",
                "auth can-i list nodes",
                "auth can-i list machineconfigpools.machineconfiguration.openshift.io",
                "get clusterversion version",
                "get clusteroperators",
                "get nodes",
                "get machineconfigpools",
            }
            self.assertTrue(all(x in allowed for x in calls), calls)
            return proc, calls

    def test_authorized_reads(self):
        p, calls = self.run_case()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(sum(x.startswith("get ") for x in calls), 4)

    def test_denied_reads(self):
        p, calls = self.run_case("deny")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse(any(x.startswith("get ") for x in calls))

    def test_authorization_api_error_fails_closed(self):
        p, calls = self.run_case("auth-error")
        self.assertNotEqual(p.returncode, 0, p.stderr)
        self.assertEqual(sum(x.startswith("auth can-i ") for x in calls), 1)
        self.assertFalse(any(x.startswith("get ") for x in calls))

    def test_ambiguous_authorization_fails_closed(self):
        p, calls = self.run_case("ambiguous-auth")
        self.assertNotEqual(p.returncode, 0, p.stderr)
        self.assertEqual(sum(x.startswith("auth can-i ") for x in calls), 1)
        self.assertFalse(any(x.startswith("get ") for x in calls))

    def test_missing_context(self):
        p, calls = self.run_case(expected_context="")
        self.assertNotEqual(p.returncode, 0)
        self.assertFalse(any(x.startswith("get ") for x in calls))

    def test_wrong_context(self):
        p, calls = self.run_case("wrong-context")
        self.assertNotEqual(p.returncode, 0)
        self.assertFalse(any(x.startswith("get ") for x in calls))

    def test_wrong_server(self):
        p, calls = self.run_case("wrong-server")
        self.assertNotEqual(p.returncode, 0)
        self.assertFalse(any(x.startswith("get ") for x in calls))

    def test_authentication_failure(self):
        p, calls = self.run_case("whoami")
        self.assertNotEqual(p.returncode, 0)
        self.assertFalse(any(x.startswith("get ") for x in calls))

    def test_version_failure(self):
        p, calls = self.run_case("version")
        self.assertNotEqual(p.returncode, 0)
        self.assertFalse(any(x.startswith("get ") for x in calls))

    def test_authorized_read_failure(self):
        p, calls = self.run_case("read")
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(sum(x.startswith("get ") for x in calls), 1)


if __name__ == "__main__":
    unittest.main()
