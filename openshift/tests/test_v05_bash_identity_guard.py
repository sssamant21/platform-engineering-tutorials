#!/usr/bin/env python3
"""Offline V04 Bash identity-guard regression tests. No real oc or kubeconfig."""
import os
import pathlib
import re
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "validation" / "V04-upgrade-etcd-recovery-evidence-worksheet.md"
MOCK = r'''#!/usr/bin/env python3
import os,sys
from pathlib import Path
args=sys.argv[1:]
with open(os.environ["OC_CALL_LOG"],"a",encoding="utf8") as f:
    f.write(" ".join(args)+"\n")
if args==["whoami"]:
    sys.exit(1 if os.getenv("FAIL_WHOAMI") else 0)
if args==["config","current-context"]:
    if os.getenv("FAIL_CONTEXT"): sys.exit(1)
    print(os.getenv("ACTUAL_CONTEXT","isolated-test"));sys.exit(0)
if args[:3]==["config","view","--minify"]:
    if os.getenv("FAIL_SERVER"):sys.exit(1)
    print(os.getenv("ACTUAL_SERVER","https://api.test.invalid:6443"));sys.exit(0)
if args==["version"]:
    print("Client Version: mock");sys.exit(0)
if args[:2]==["auth","can-i"]:
    print(os.getenv("AUTH_RESULT","yes"));sys.exit(0)
if args and args[0]=="get":
    print("mock read");sys.exit(0)
sys.exit(97)
'''

def bash_snippet():
    source=SOURCE.read_text(encoding="utf8")
    match=re.search(r"```sh\n(.*?)\n```",source,re.S)
    if not match: raise AssertionError("V04 Bash fenced snippet missing")
    return match.group(1)+"\n"

class IdentityGuardTests(unittest.TestCase):
    def run_case(self, changes, expected_get):
        with tempfile.TemporaryDirectory(prefix="oc-v05-") as d:
            directory=pathlib.Path(d)
            oc=directory/"oc"
            oc.write_text(MOCK,encoding="utf8")
            oc.chmod(0o700)
            script=directory/"preflight.sh"
            script.write_text(bash_snippet(),encoding="utf8")
            log=directory/"calls.log"
            env=os.environ.copy()
            for key in ("EXPECTED_CONTEXT","EXPECTED_SERVER","ACTUAL_CONTEXT",
                        "ACTUAL_SERVER","FAIL_WHOAMI","FAIL_CONTEXT","FAIL_SERVER",
                        "AUTH_RESULT","KUBECONFIG"):
                env.pop(key,None)
            env.update({"PATH":str(directory)+os.pathsep+os.environ.get("PATH",""),
                        "HOME":str(directory),"KUBECONFIG":str(directory/"nonexistent"),
                        "OC_CALL_LOG":str(log),
                        "EXPECTED_CONTEXT":"isolated-test",
                        "EXPECTED_SERVER":"https://api.test.invalid:6443"})
            env.update(changes)
            result=subprocess.run(["bash",str(script)],env=env,cwd=directory,
                                  text=True,capture_output=True,timeout=15)
            calls=log.read_text(encoding="utf8").splitlines() if log.exists() else []
            self.assertFalse(any(c.startswith(("patch ","delete ","apply ","adm ","debug ","drain ")) for c in calls),calls)
            gets=[c for c in calls if c.startswith("get ")]
            self.assertEqual(bool(gets),expected_get,(result.returncode,calls,result.stderr))
            return result,calls

    def test_missing_context(self):
        self.run_case({"EXPECTED_CONTEXT":""},False)
    def test_missing_server(self):
        self.run_case({"EXPECTED_SERVER":""},False)
    def test_authentication_failure(self):
        self.run_case({"FAIL_WHOAMI":"1"},False)
    def test_context_lookup_failure(self):
        self.run_case({"FAIL_CONTEXT":"1"},False)
    def test_wrong_context(self):
        self.run_case({"ACTUAL_CONTEXT":"other"},False)
    def test_server_lookup_failure(self):
        self.run_case({"FAIL_SERVER":"1"},False)
    def test_wrong_server(self):
        self.run_case({"ACTUAL_SERVER":"https://wrong.test.invalid:6443"},False)
    def test_authorized_reads(self):
        result,calls=self.run_case({},True)
        self.assertEqual(sum(c.startswith("get ") for c in calls),4)
        self.assertEqual(result.returncode,0)
    def test_denied_reads(self):
        _,calls=self.run_case({"AUTH_RESULT":"no"},False)
        self.assertEqual(sum(c.startswith("auth can-i ") for c in calls),4)

if __name__=="__main__":
    unittest.main()
