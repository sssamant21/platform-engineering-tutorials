import unittest,json,hashlib
from dataclasses import replace
from io import StringIO
from contextlib import redirect_stdout
from supply_chain_lab import SupplyError,Dependency,Finding,ReleasePlan,inventory,sbom,assess,drift,verify_artifact,paginate,Pager,gate,samples,demo,main
class Tests(unittest.TestCase):
    def setUp(self):
        self.deps=samples();self.report=sbom(self.deps)
        self.plan=ReleasePlan("python-sre","1"*64,"2"*64,self.report["digest"],"INC-105")
    def reject(self,fn):
        with self.assertRaises(SupplyError):fn()
    def test_valid(self):self.deps[0].validate()
    def test_name(self):self.reject(lambda:replace(self.deps[0],name="../bad").validate())
    def test_version(self):self.reject(lambda:replace(self.deps[0],version="latest").validate())
    def test_hash(self):self.reject(lambda:replace(self.deps[0],sha256="bad").validate())
    def test_direct(self):self.reject(lambda:replace(self.deps[0],direct=1).validate())
    def test_source(self):self.reject(lambda:replace(self.deps[0],source="http").validate())
    def test_normalized(self):self.assertEqual(Dependency("My_Pkg","1.2","a"*64,True,"pypi").key(),"my-pkg")
    def test_duplicate(self):self.reject(lambda:inventory([Dependency("my_pkg","1.2","a"*64,True,"pypi"),Dependency("my-pkg","1.2","b"*64,True,"pypi")]))
    def test_invalid_record(self):self.reject(lambda:inventory([{}]))
    def test_sbom(self):self.assertEqual(len(self.report["packages"]),3)
    def test_sorted(self):self.assertEqual([x["name"] for x in self.report["packages"]],sorted(x["name"] for x in self.report["packages"]))
    def test_sbom_stable(self):self.assertEqual(self.report["digest"],sbom(list(reversed(self.deps)))["digest"])
    def test_sbom_not_standard(self):self.assertIn("not-cyclonedx",self.report["format"])
    def test_partial(self):self.assertEqual(assess(self.deps,[],False)["risk"],"unknown")
    def test_risk(self):self.assertEqual(assess(self.deps,[Finding("urllib3","2.2.3","DEMO-1","high")])["risk"],"review")
    def test_no_matches(self):self.assertEqual(assess(self.deps,[])["risk"],"no-matches-in-synthetic-feed")
    def test_unmatched(self):self.assertEqual(assess(self.deps,[Finding("urllib3","9.9","DEMO-1","high")])["vulnerabilities"],[])
    def test_finding_invalid(self):self.reject(lambda:assess(self.deps,[Finding("urllib3","2.2.3","DEMO-1","urgent")]))
    def test_drift_removed(self):self.assertEqual(drift(inventory(self.deps),inventory(self.deps[:2]))["removed"],1)
    def test_drift_changed(self):self.assertEqual(drift(inventory(self.deps),inventory([replace(self.deps[0],version="2.32.4")]+self.deps[1:]))["changed"],1)
    def test_drift_unknown(self):self.assertIsNone(drift(inventory(self.deps,False),inventory(self.deps))["removed"])
    def test_artifact(self):
        data=b"synthetic artifact";self.assertTrue(verify_artifact(data,hashlib.sha256(data).hexdigest()))
    def test_artifact_tamper(self):self.assertFalse(verify_artifact(b"other",hashlib.sha256(b"original").hexdigest()))
    def test_artifact_invalid(self):self.reject(lambda:verify_artifact("text","a"*64))
    def test_pagination(self):self.assertEqual(paginate(Pager([1,2,3],1).fetch),[1,2,3])
    def test_empty(self):self.assertEqual(paginate(Pager([]).fetch),[])
    def test_page_budget(self):self.reject(lambda:paginate(Pager([1,2,3],1).fetch,max_pages=2))
    def test_item_budget(self):self.reject(lambda:paginate(Pager([1,2,3],1).fetch,max_items=2))
    def test_loop(self):self.reject(lambda:paginate(lambda t:{"items":[],"next":"repeat"}))
    def test_bad_page(self):self.reject(lambda:paginate(lambda t:{"items":None}))
    def test_invalid_budget(self):self.reject(lambda:paginate(Pager([]).fetch,max_pages=0))
    def test_plan(self):self.assertEqual(self.plan.digest(),self.plan.digest())
    def test_plan_change(self):self.assertNotEqual(self.plan.digest(),replace(self.plan,sbom_digest="3"*64).digest())
    def test_plan_invalid(self):self.reject(lambda:replace(self.plan,commit_sha="bad").digest())
    def approval(self):return {"approved":True,"digest":self.plan.digest(),"owner":"devops","approver":"security","expires_at":200,"rollback_tested":True}
    def test_hold(self):self.assertEqual(gate(self.plan)["decision"],"hold")
    def test_approved(self):self.assertEqual(gate(self.plan,self.approval(),100)["decision"],"advisory-only")
    def test_expired(self):self.assertEqual(gate(self.plan,self.approval(),200)["decision"],"hold")
    def test_self_approval(self):
        a=self.approval();a["approver"]="devops";self.assertEqual(gate(self.plan,a,100)["decision"],"hold")
    def test_wrong_digest(self):
        a=self.approval();a["digest"]="bad";self.assertEqual(gate(self.plan,a,100)["decision"],"hold")
    def test_no_rollback(self):
        a=self.approval();a["rollback_tested"]=False;self.assertEqual(gate(self.plan,a,100)["decision"],"hold")
    def test_no_writes(self):self.assertEqual(gate(self.plan,self.approval(),100,False)["mutations"],0)
    def test_no_signature(self):self.assertFalse(demo()["cryptographic_signatures_verified"])
    def test_no_scan(self):self.assertFalse(demo()["actual_vulnerability_scan"])
    def test_no_network(self):self.assertEqual(demo()["network_calls"],0)
    def test_cli(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(out.getvalue())["sbom"]["complete"],True)
if __name__=="__main__":unittest.main()
