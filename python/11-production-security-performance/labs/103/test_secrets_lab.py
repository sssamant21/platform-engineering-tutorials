import unittest,json
from dataclasses import replace
from contextlib import redirect_stdout
from io import StringIO
from secrets_lab import Secret,LabError,evaluate,paginate,Pager,RotationPlan,gate,samples,demo,main
class Tests(unittest.TestCase):
    def setUp(self):
        self.rs=samples()
        self.p=RotationPlan("aws","123456789012",self.rs[0].resource_id,"v7","kms-v2","INC-103")
    def reject(self,fn):
        with self.assertRaises(LabError):fn()
    def test_four_providers(self):self.assertEqual({r.provider for r in self.rs},{"aws","azure","gcp","kubernetes"})
    def test_valid(self):self.rs[0].validate()
    def test_provider(self):self.reject(lambda:replace(self.rs[0],provider="other").validate())
    def test_scope(self):self.reject(lambda:replace(self.rs[0],scope="../bad").validate())
    def test_owner_type(self):self.reject(lambda:replace(self.rs[0],owner=123).validate())
    def test_age(self):self.reject(lambda:replace(self.rs[0],age_days=-1).validate())
    def test_bool(self):self.reject(lambda:replace(self.rs[0],tls_required=1).validate())
    def test_azure_case(self):self.assertEqual(self.rs[1].key(),replace(self.rs[1],resource_id=self.rs[1].resource_id.upper()).key())
    def test_overdue(self):self.assertIn("rotation-overdue",{f["policy"] for f in evaluate(self.rs)["findings"]})
    def test_at_rest(self):self.assertIn("at-rest-unverified",{f["policy"] for f in evaluate(self.rs)["findings"]})
    def test_identity(self):self.assertIn("static-credential-review",{f["policy"] for f in evaluate(self.rs)["findings"]})
    def test_audit(self):self.assertIn("audit-disabled",{f["policy"] for f in evaluate(self.rs)["findings"]})
    def test_unknown(self):self.assertIn("rotation-unknown",{f["policy"] for f in evaluate(self.rs)["findings"]})
    def test_owner(self):self.assertIn("missing-owner",{f["policy"] for f in evaluate([replace(self.rs[0],owner=None)])["findings"]})
    def test_tls(self):self.assertIn("tls-required",{f["policy"] for f in evaluate([replace(self.rs[0],tls_required=False)])["findings"]})
    def test_clean(self):self.assertEqual(evaluate([self.rs[1]])["findings"],[])
    def test_partial(self):self.assertEqual(evaluate(self.rs,False)["compliance"],"unknown")
    def test_duplicate(self):self.reject(lambda:evaluate([self.rs[0]]*2))
    def test_invalid_record(self):self.reject(lambda:evaluate([{}]))
    def test_pagination(self):self.assertEqual(paginate(Pager([1,2,3],1).fetch),[1,2,3])
    def test_empty(self):self.assertEqual(paginate(Pager([]).fetch),[])
    def test_page_limit(self):self.reject(lambda:paginate(Pager([1,2,3],1).fetch,max_pages=2))
    def test_item_limit(self):self.reject(lambda:paginate(Pager([1,2,3],1).fetch,max_items=2))
    def test_loop(self):self.reject(lambda:paginate(lambda t:{"items":[],"next":"repeat"}))
    def test_malformed_page(self):self.reject(lambda:paginate(lambda t:{"items":None}))
    def test_invalid_budget(self):self.reject(lambda:paginate(Pager([]).fetch,max_pages=0))
    def test_digest(self):self.assertEqual(self.p.digest(),self.p.digest())
    def test_version_bound(self):self.assertNotEqual(self.p.digest(),replace(self.p,expected_version="v8").digest())
    def test_key_version_bound(self):self.assertNotEqual(self.p.digest(),replace(self.p,expected_key_version="kms-v3").digest())
    def test_delete_rejected(self):self.reject(lambda:replace(self.p,action="delete-key").digest())
    def test_invalid_plan(self):self.reject(lambda:replace(self.p,ticket="../bad").digest())
    def approval(self):return {"approved":True,"digest":self.p.digest(),"owner":"dbre","approver":"security","expires_at":200,"rollback_tested":True,"consumers_verified":True}
    def test_hold(self):self.assertEqual(gate(self.p)["decision"],"hold")
    def test_approved(self):self.assertEqual(gate(self.p,self.approval(),100)["decision"],"advisory-only")
    def test_expired(self):self.assertFalse(gate(self.p,self.approval(),200)["approval_valid"])
    def test_self_approval(self):
        a=self.approval();a["approver"]="dbre"
        self.assertFalse(gate(self.p,a,100)["approval_valid"])
    def test_bad_digest(self):
        a=self.approval();a["digest"]="bad"
        self.assertFalse(gate(self.p,a,100)["approval_valid"])
    def test_rollback(self):
        a=self.approval();a["rollback_tested"]=False
        self.assertFalse(gate(self.p,a,100)["approval_valid"])
    def test_consumers(self):
        a=self.approval();a["consumers_verified"]=False
        self.assertFalse(gate(self.p,a,100)["approval_valid"])
    def test_no_secret_reads(self):self.assertEqual(demo()["secret_reads"],0)
    def test_no_crypto(self):self.assertEqual(demo()["cryptographic_operations"],0)
    def test_no_writes(self):self.assertEqual(gate(self.p,self.approval(),100,False)["mutations"],0)
    def test_no_network(self):self.assertEqual(demo()["network_calls"],0)
    def test_cli(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(out.getvalue())["resources"],4)
if __name__=="__main__":unittest.main()
