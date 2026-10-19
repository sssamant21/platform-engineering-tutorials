import unittest,json
from dataclasses import replace
from io import StringIO
from contextlib import redirect_stdout
from audit_lab import AuditError,Evidence,ExceptionRecord,Plan,assess,drift,paginate,Pager,approval_gate,samples,demo,main,digest
class Tests(unittest.TestCase):
    def setUp(self):
        self.rows=samples()
        self.report=assess(self.rows,now=1100)
        self.plan=Plan("azure","sub-stage","aks/cluster","least-privilege","INC-104",self.report["report_sha256"])
    def reject(self,fn):
        with self.assertRaises(AuditError):fn()
    def test_providers(self):self.assertEqual({r.provider for r in self.rows},{"aws","azure","gcp","kubernetes"})
    def test_valid(self):self.rows[0].validate()
    def test_provider(self):self.reject(lambda:replace(self.rows[0],provider="other").validate())
    def test_control(self):self.reject(lambda:replace(self.rows[0],control="delete").validate())
    def test_scope(self):self.reject(lambda:replace(self.rows[0],scope="../bad").validate())
    def test_owner_type(self):self.reject(lambda:replace(self.rows[0],owner=2).validate())
    def test_pass_type(self):self.reject(lambda:replace(self.rows[0],passed=1).validate())
    def test_timestamp(self):self.reject(lambda:replace(self.rows[0],observed_at=-1).validate())
    def test_pass(self):self.assertEqual(self.report["passed"],2)
    def test_fail(self):self.assertIn("fail",{f["status"] for f in self.report["findings"]})
    def test_owner(self):self.assertIn("owner-required",{f["control"] for f in self.report["findings"] if f["status"]=="fail"})
    def test_stale(self):self.assertEqual(assess([self.rows[0]],now=5000)["findings"][0]["status"],"unknown")
    def test_future(self):self.assertEqual(assess([self.rows[0]],now=900)["findings"][0]["status"],"unknown")
    def test_partial(self):self.assertEqual(assess(self.rows,now=1100,complete=False)["coverage"],"unknown")
    def test_not_certified(self):self.assertFalse(self.report["compliance_certified"])
    def test_duplicate(self):self.reject(lambda:assess([self.rows[0]]*2,now=1100))
    def test_invalid_record(self):self.reject(lambda:assess([{}],now=1100))
    def test_digest(self):self.assertEqual(self.report["report_sha256"],assess(self.rows,now=1100)["report_sha256"])
    def test_digest_tamper(self):self.assertNotEqual(digest({"x":1}),digest({"x":2}))
    def test_exception(self):
        e=ExceptionRecord(self.rows[1].key(),"INC-EX","security",1200,"risk-accepted")
        report=assess(self.rows,now=1100,exceptions=[e])
        self.assertIn("excepted",{f["status"] for f in report["findings"]})
    def test_expired_exception(self):
        e=ExceptionRecord(self.rows[1].key(),"INC-EX","security",1100,"risk-accepted")
        self.assertIn("fail",{f["status"] for f in assess(self.rows,now=1100,exceptions=[e])["findings"]})
    def test_invalid_exception(self):
        e=ExceptionRecord(self.rows[1].key(),"INC-EX","security",1200,"")
        self.reject(lambda:assess(self.rows,now=1100,exceptions=[e]))
    def test_duplicate_exception(self):
        e=ExceptionRecord(self.rows[1].key(),"INC-EX","security",1200,"risk-accepted")
        self.reject(lambda:assess(self.rows,now=1100,exceptions=[e,e]))
    def test_drift(self):
        old=assess([replace(self.rows[1],passed=True)],now=1100)
        new=assess([self.rows[1]],now=1100)
        self.assertEqual(drift(old,new)["new_failures"],1)
    def test_partial_drift(self):
        self.assertIsNone(drift(assess(self.rows,now=1100,complete=False),self.report)["new_failures"])
    def test_pagination(self):self.assertEqual(paginate(Pager([1,2,3],1).fetch),[1,2,3])
    def test_empty(self):self.assertEqual(paginate(Pager([]).fetch),[])
    def test_page_limit(self):self.reject(lambda:paginate(Pager([1,2,3],1).fetch,max_pages=2))
    def test_item_limit(self):self.reject(lambda:paginate(Pager([1,2,3],1).fetch,max_items=2))
    def test_loop(self):self.reject(lambda:paginate(lambda t:{"items":[],"next":"repeat"}))
    def test_bad_page(self):self.reject(lambda:paginate(lambda t:{"items":None}))
    def test_budget(self):self.reject(lambda:paginate(Pager([]).fetch,max_pages=0))
    def test_plan_digest(self):self.assertEqual(self.plan.fingerprint(),self.plan.fingerprint())
    def test_plan_invalid(self):self.reject(lambda:replace(self.plan,control="delete").fingerprint())
    def test_plan_evidence_bound(self):self.assertNotEqual(self.plan.fingerprint(),replace(self.plan,expected_evidence_digest="other").fingerprint())
    def approval(self):return {"approved":True,"digest":self.plan.fingerprint(),"owner":"platform","approver":"security","expires_at":200,"rollback_tested":True}
    def test_hold(self):self.assertEqual(approval_gate(self.plan)["decision"],"hold")
    def test_approved(self):self.assertEqual(approval_gate(self.plan,self.approval(),100)["decision"],"advisory-only")
    def test_expired(self):self.assertFalse(approval_gate(self.plan,self.approval(),200)["approval_valid"])
    def test_self_approval(self):
        a=self.approval();a["approver"]="platform"
        self.assertFalse(approval_gate(self.plan,a,100)["approval_valid"])
    def test_bad_digest(self):
        a=self.approval();a["digest"]="bad"
        self.assertFalse(approval_gate(self.plan,a,100)["approval_valid"])
    def test_rollback(self):
        a=self.approval();a["rollback_tested"]=False
        self.assertFalse(approval_gate(self.plan,a,100)["approval_valid"])
    def test_no_mutations(self):self.assertEqual(approval_gate(self.plan,self.approval(),100,False)["mutations"],0)
    def test_no_network(self):self.assertEqual(demo()["network_calls"],0)
    def test_cli(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(out.getvalue())["report"]["total"],4)
if __name__=="__main__":unittest.main()
