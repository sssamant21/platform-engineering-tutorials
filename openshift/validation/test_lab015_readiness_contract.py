"""Offline source-contract checks for Lab 015. No oc, credentials or cluster required.

Run: python -m unittest discover -s openshift/validation -p 'test_lab015_readiness_contract.py' -v
These are static safeguards, NOT mock execution or OCP runtime certification.
"""
from pathlib import Path
import re
import unittest

LAB = Path(__file__).resolve().parents[1] / "labs" / "015-recovery-read-only-readiness-audit.md"


def blocks():
    source = LAB.read_text(encoding="utf-8")
    bash = re.search(r"```bash\n(.*?)\n```", source, re.S)
    ps = re.search(r"```powershell\n(.*?)\n```", source, re.S)
    if not bash or not ps:
        raise AssertionError("Both executable examples must exist")
    return bash.group(1), ps.group(1)


class Lab015SourceContract(unittest.TestCase):
    def test_lab_exists(self):
        self.assertTrue(LAB.is_file())

    def test_bash_identity_precedes_resource_queries(self):
        bash, _ = blocks()
        checks = [': "${EXPECTED_API_SERVER:', 'oc whoami', 'oc config current-context',
                  'oc config view --minify', 'API server mismatch', 'oc version', 'check_read()']
        positions = [bash.index(x) for x in checks]
        self.assertEqual(positions, sorted(positions))

    def test_powershell_identity_precedes_reads(self):
        _, ps = blocks()
        checks = ['IsNullOrWhiteSpace($ExpectedApiServer)', 'oc whoami',
                  'oc config current-context', 'oc config view --minify',
                  'server mismatch', 'oc version', 'function Invoke-ReadIfAuthorized']
        positions = [ps.index(x) for x in checks]
        self.assertEqual(positions, sorted(positions))

    def test_bash_authorization_fail_closed(self):
        bash, _ = blocks()
        for required in ['answer="$(oc auth can-i', 'if [ "$rc" -ne 0 ]',
                         'if [ "$answer" != "yes" ]', 'return 2',
                         'if ! oc "$@"', 'failures=1', '[ "$failures" -eq 0 ]']:
            self.assertIn(required, bash)

    def test_powershell_authorization_fail_closed(self):
        _, ps = blocks()
        for required in ['$authExit = $LASTEXITCODE', 'if ($authExit -ne 0)',
                         "-cne 'yes'", "return 'SKIP'", '$readExit = $LASTEXITCODE',
                         "return 'ERROR'", "if ($results -contains 'ERROR')"]:
            self.assertIn(required, ps)

    def test_four_read_operations_match_permissions(self):
        bash, ps = blocks()
        expected = [
            ('get clusterversions.config.openshift.io --resource-name=version',
             "'get','clusterversions.config.openshift.io','--resource-name=version'"),
            ('list clusteroperators.config.openshift.io',
             "'list','clusteroperators.config.openshift.io'"),
            ('list nodes', "'list','nodes'"),
            ('get infrastructures.config.openshift.io --resource-name=cluster',
             "'get','infrastructures.config.openshift.io','--resource-name=cluster'"),
        ]
        self.assertEqual(bash.count("check_read '"), 4)
        self.assertEqual(ps.count("(Invoke-ReadIfAuthorized -Description"), 4)
        for b, p in expected:
            self.assertIn(b, bash)
            self.assertIn(p, ps)

    def test_no_mutating_oc_commands_in_examples(self):
        bash, ps = blocks()
        for script in (bash, ps):
            self.assertNotRegex(script, r"(?m)^\s*(?:\$null\s*=\s*)?(?:&\s*)?oc\s+(?:delete|apply|patch|replace|create|adm\s+(?:drain|upgrade))\b")

    def test_no_raw_kubeconfig_or_secret_reads(self):
        bash, ps = blocks()
        for script in (bash, ps):
            self.assertNotIn('oc config view --raw', script)
            self.assertNotRegex(script, r"(?m)^\s*oc\s+get\s+secrets?\b")


if __name__ == "__main__":
    unittest.main()
