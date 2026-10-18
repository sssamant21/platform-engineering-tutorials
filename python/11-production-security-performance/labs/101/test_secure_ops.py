import hashlib,json,unittest
from io import StringIO
from contextlib import redirect_stdout
from dataclasses import replace
from secure_ops import (SecurityError,Dependency,validate_request,authorize,safe_workspace_path,
    validate_endpoint,redact,verify_digest,audit_event,advisory_plan,approval_gate,demo,main)
class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.req={"service":"patient-api","environment":"staging","limit":20,"request_id":"req-101"}
        self.actor={"subject":"sre-viewer","roles":["viewer"],"environments":["staging"]}
        self.plan=advisory_plan("read-inventory","patient-api","staging","inc-101")
    def fails(self,fn):
        with self.assertRaises(SecurityError):fn()
    def test_valid_request(self):self.assertEqual(validate_request(self.req),self.req)
    def test_unknown_field(self):self.fails(lambda:validate_request({**self.req,"admin":True}))
    def test_missing_field(self):self.fails(lambda:validate_request({"service":"x"}))
    def test_bad_service(self):self.fails(lambda:validate_request({**self.req,"service":"../root"}))
    def test_bad_environment(self):self.fails(lambda:validate_request({**self.req,"environment":"production"}))
    def test_boolean_limit(self):self.fails(lambda:validate_request({**self.req,"limit":True}))
    def test_limit_bounds(self):self.fails(lambda:validate_request({**self.req,"limit":101}))
    def test_bad_request_id(self):self.fails(lambda:validate_request({**self.req,"request_id":"INVALID"}))
    def test_authorized(self):self.assertTrue(authorize(self.actor,"read-inventory","staging"))
    def test_denied_action(self):self.assertFalse(authorize(self.actor,"review-policy","staging"))
    def test_denied_environment(self):self.assertFalse(authorize(self.actor,"read-inventory","prod"))
    def test_unknown_role(self):self.assertFalse(authorize({**self.actor,"roles":["admin"]},"read-inventory","staging"))
    def test_auditor(self):self.assertTrue(authorize({**self.actor,"roles":["auditor"]},"review-incident","staging"))
    def test_invalid_actor(self):self.assertFalse(authorize({"subject":"x"},"read-inventory","staging"))
    def test_path_valid(self):self.assertEqual(safe_workspace_path("logs/staging"),"logs/staging")
    def test_path_parent(self):self.fails(lambda:safe_workspace_path("logs/../etc"))
    def test_path_absolute(self):self.fails(lambda:safe_workspace_path("/etc"))
    def test_path_backslash(self):self.fails(lambda:safe_workspace_path("logs\\secret"))
    def test_path_percent(self):self.fails(lambda:safe_workspace_path("logs%2fsecret"))
    def test_public_ip(self):self.assertEqual(validate_endpoint("8.8.8.8"),"8.8.8.8")
    def test_loopback(self):self.fails(lambda:validate_endpoint("127.0.0.1"))
    def test_private(self):self.fails(lambda:validate_endpoint("10.0.0.1"))
    def test_metadata(self):self.fails(lambda:validate_endpoint("169.254.169.254"))
    def test_dns(self):self.fails(lambda:validate_endpoint("example.com"))
    def test_redact(self):self.assertEqual(redact({"password":"x"})["password"],"***REDACTED***")
    def test_nested_redact(self):self.assertEqual(redact({"x":[{"token":"x"}]})["x"][0]["token"],"***REDACTED***")
    def test_safe_log(self):self.assertEqual(redact({"count":3}),{"count":3})
    def test_hash(self):self.assertTrue(verify_digest(b"data",hashlib.sha256(b"data").hexdigest()))
    def test_wrong_hash(self):self.assertFalse(verify_digest(b"data","0"*64))
    def test_bad_hash(self):self.fails(lambda:verify_digest(b"data","bad"))
    def test_dep_valid(self):Dependency("sample-lib","1.2.3","a"*64,True).validate()
    def test_dep_unpinned(self):self.fails(lambda:Dependency("sample-lib","latest","a"*64,True).validate())
    def test_dep_hash(self):self.fails(lambda:Dependency("sample-lib","1.2.3","bad",True).validate())
    def test_audit(self):self.assertEqual(audit_event("sre-viewer","read-inventory","staging","allow","req-101")["decision"],"allow")
    def test_audit_invalid(self):self.fails(lambda:audit_event("sre-viewer","delete","staging","allow","req-101"))
    def test_plan_stable(self):self.assertEqual(self.plan,advisory_plan("read-inventory","patient-api","staging","inc-101"))
    def test_plan_reject_delete(self):self.fails(lambda:advisory_plan("delete","patient-api","staging","inc-101"))
    def test_plan_tamper(self):self.fails(lambda:approval_gate({**self.plan,"digest":"0"*64}))
    def test_default_hold(self):self.assertEqual(approval_gate(self.plan)["decision"],"hold")
    def approved(self):
        return {"approved":True,"digest":self.plan["digest"],"owner":"dbre","approver":"security",
                "rollback_tested":True,"expires_at":200}
    def test_approved(self):self.assertEqual(approval_gate(self.plan,self.approved(),100)["decision"],"advisory-only")
    def test_expired(self):self.assertFalse(approval_gate(self.plan,self.approved(),200)["approved"])
    def test_self_approval(self):
        a=self.approved();a["approver"]="dbre"
        self.assertFalse(approval_gate(self.plan,a,100)["approved"])
    def test_no_rollback(self):
        a=self.approved();a["rollback_tested"]=False
        self.assertFalse(approval_gate(self.plan,a,100)["approved"])
    def test_wrong_digest(self):
        a=self.approved();a["digest"]="0"*64
        self.assertFalse(approval_gate(self.plan,a,100)["approved"])
    def test_no_writes(self):self.assertEqual(approval_gate(self.plan,self.approved(),100)["mutations"],0)
    def test_demo_no_network(self):self.assertEqual(demo()["network_calls"],0)
    def test_demo_no_secrets(self):self.assertEqual(demo()["secret_reads"],0)
    def test_cli(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(out.getvalue())["mode"],"offline")
if __name__=="__main__":unittest.main()
