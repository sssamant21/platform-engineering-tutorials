import json,unittest
from dataclasses import replace
from io import StringIO
from contextlib import redirect_stdout
from identity_lab import IdentityError,VerifiedPrincipal,Resource,Request,authorize,fingerprint,examples,demo,main
class Tests(unittest.TestCase):
    def setUp(self):self.p,self.r=examples()
    def fails(self,fn):
        with self.assertRaises(IdentityError):fn()
    def test_valid(self):self.p.validate(150,"https://issuer.example","sre-api")
    def test_expired(self):self.fails(lambda:replace(self.p,expires_at=150).validate(150,"https://issuer.example","sre-api"))
    def test_not_before(self):self.fails(lambda:replace(self.p,not_before=151).validate(150,"https://issuer.example","sre-api"))
    def test_issuer(self):self.fails(lambda:self.p.validate(150,"https://other","sre-api"))
    def test_audience(self):self.fails(lambda:self.p.validate(150,"https://issuer.example","other"))
    def test_bad_subject(self):self.fails(lambda:replace(self.p,subject="../x").validate(150,"https://issuer.example","sre-api"))
    def test_role(self):self.fails(lambda:replace(self.p,roles=("admin",)).validate(150,"https://issuer.example","sre-api"))
    def test_scope(self):self.fails(lambda:replace(self.p,scopes=("bad scope",)).validate(150,"https://issuer.example","sre-api"))
    def test_resource(self):self.r.resource.validate()
    def test_invalid_resource(self):self.fails(lambda:replace(self.r.resource,name="../bad").validate())
    def test_action(self):self.fails(lambda:replace(self.r,action="delete-db").validate())
    def test_fingerprint(self):self.assertEqual(fingerprint(self.p,self.r),fingerprint(self.p,self.r))
    def test_fingerprint_scope(self):self.assertNotEqual(fingerprint(self.p,self.r),fingerprint(self.p,replace(self.r,resource=replace(self.r.resource,tenant="tenant-b"))))
    def test_cross_tenant(self):
        r=replace(self.r,resource=replace(self.r.resource,tenant="tenant-b"))
        self.assertEqual(authorize(self.p,r,now=150)["reason"],"tenant-mismatch")
    def test_rbac(self):
        p=replace(self.p,roles=("viewer",))
        self.assertEqual(authorize(p,self.r,now=150)["reason"],"rbac-deny")
    def test_scope_denial(self):
        p=replace(self.p,scopes=("read",))
        self.assertEqual(authorize(p,self.r,now=150)["reason"],"scope-deny")
    def test_missing_approval(self):self.assertEqual(authorize(self.p,self.r,now=150)["reason"],"approval-required")
    def approval(self):return {"approved":True,"digest":fingerprint(self.p,self.r),"approver":"security","expires_at":180,"rollback_tested":True}
    def test_approved(self):self.assertTrue(authorize(self.p,self.r,now=150,approval=self.approval())["allowed"])
    def test_wrong_digest(self):
        a=self.approval();a["digest"]="bad"
        self.assertFalse(authorize(self.p,self.r,now=150,approval=a)["allowed"])
    def test_self_approval(self):
        a=self.approval();a["approver"]=self.p.subject
        self.assertEqual(authorize(self.p,self.r,now=150,approval=a)["reason"],"separation-of-duties")
    def test_expired_approval(self):
        a=self.approval();a["expires_at"]=150
        self.assertFalse(authorize(self.p,self.r,now=150,approval=a)["allowed"])
    def test_rollback(self):
        a=self.approval();a["rollback_tested"]=False
        self.assertFalse(authorize(self.p,self.r,now=150,approval=a)["allowed"])
    def test_staging(self):
        r=replace(self.r,resource=replace(self.r.resource,environment="staging"))
        self.assertTrue(authorize(self.p,r,now=150)["allowed"])
    def test_read(self):
        r=Request("read",self.r.resource)
        self.assertTrue(authorize(self.p,r,now=150)["allowed"])
    def test_replay(self):
        seen=set();a=self.approval()
        self.assertTrue(authorize(self.p,self.r,now=150,approval=a,seen=seen)["allowed"])
        self.assertEqual(authorize(self.p,self.r,now=150,approval=a,seen=seen)["reason"],"replay")
    def test_audit_redacted(self):
        result=authorize(self.p,self.r,now=150)
        self.assertNotIn(self.p.subject,json.dumps(result))
        self.assertIn("subject_hash",result)
    def test_no_writes(self):self.assertEqual(authorize(self.p,self.r,now=150)["mutations"],0)
    def test_no_network(self):self.assertEqual(demo()["network_calls"],0)
    def test_no_jwt_verification(self):self.assertFalse(demo()["jwt_signature_verification"])
    def test_cli(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(out.getvalue())["tokens_issued"],0)
if __name__=="__main__":unittest.main()
