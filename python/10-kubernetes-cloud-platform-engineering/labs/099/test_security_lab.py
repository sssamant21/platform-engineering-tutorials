import json,unittest
from dataclasses import replace
from contextlib import redirect_stdout
from io import StringIO
from security_lab import SecretMetadata,PolicyError,evaluate,paginate,Plan,approval_gate,FakePager,sample,demo,main
class Tests(unittest.TestCase):
    def setUp(self):
        self.resources=sample()
        self.plan=Plan("aws","123456789012",self.resources[0].resource_id,"propose-rotation","INC-099","v17")
    def fails(self,fn):
        with self.assertRaises(PolicyError):fn()
    def test_all_providers(self):self.assertEqual({r.provider for r in self.resources},{"aws","azure","gcp","kubernetes"})
    def test_valid(self):self.resources[0].validate()
    def test_invalid_provider(self):self.fails(lambda:replace(self.resources[0],provider="other").validate())
    def test_invalid_scope(self):self.fails(lambda:replace(self.resources[0],scope="../bad").validate())
    def test_invalid_owner(self):self.fails(lambda:replace(self.resources[0],owner=5).validate())
    def test_invalid_age(self):self.fails(lambda:replace(self.resources[0],age_days=-1).validate())
    def test_invalid_boolean(self):self.fails(lambda:replace(self.resources[0],public_access=1).validate())
    def test_overdue(self):self.assertIn("rotation-overdue",{f.policy for f in evaluate(self.resources)})
    def test_audit(self):self.assertIn("audit-required",{f.policy for f in evaluate(self.resources)})
    def test_identity(self):self.assertIn("workload-identity-preferred",{f.policy for f in evaluate(self.resources)})
    def test_unknown_age(self):self.assertIn("rotation-age-unknown",{f.policy for f in evaluate(self.resources)})
    def test_owner(self):
        r=replace(self.resources[0],owner=None)
        self.assertIn("production-owner-required",{f.policy for f in evaluate([r])})
    def test_public(self):
        r=replace(self.resources[0],public_access=True)
        self.assertIn("public-access-review",{f.policy for f in evaluate([r])})
    def test_clean(self):self.assertEqual(evaluate([self.resources[1]]),[])
    def test_duplicate(self):self.fails(lambda:evaluate([self.resources[0]]*2))
    def test_invalid_record(self):self.fails(lambda:evaluate([{}]))
    def test_pages(self):self.assertEqual(paginate(FakePager([1,2,3],1).fetch),[1,2,3])
    def test_empty(self):self.assertEqual(paginate(FakePager([]).fetch),[])
    def test_page_limit(self):self.fails(lambda:paginate(FakePager([1,2,3],1).fetch,max_pages=2))
    def test_item_limit(self):self.fails(lambda:paginate(FakePager([1,2,3],1).fetch,max_items=2))
    def test_loop(self):self.fails(lambda:paginate(lambda t:{"items":[],"next":"repeat"}))
    def test_malformed_page(self):self.fails(lambda:paginate(lambda t:{"items":None}))
    def test_invalid_budget(self):self.fails(lambda:paginate(FakePager([]).fetch,max_pages=0))
    def test_digest_stable(self):self.assertEqual(self.plan.digest(),self.plan.digest())
    def test_plan_action_rejected(self):self.fails(lambda:replace(self.plan,action="delete-secret").digest())
    def test_plan_scope_rejected(self):self.fails(lambda:replace(self.plan,scope="../prod").digest())
    def test_hold(self):self.assertEqual(approval_gate(self.plan)["decision"],"hold")
    def approved(self):
        return {"approved":True,"digest":self.plan.digest(),"owner":"dbre","approver":"security",
                "rollback_tested":True,"expires_at":200}
    def test_valid_approval(self):self.assertTrue(approval_gate(self.plan,self.approved(),100)["approval_valid"])
    def test_expired(self):self.assertFalse(approval_gate(self.plan,self.approved(),200)["approval_valid"])
    def test_self_approval(self):
        a=self.approved();a["approver"]="dbre"
        self.assertFalse(approval_gate(self.plan,a,100)["approval_valid"])
    def test_wrong_digest(self):
        a=self.approved();a["digest"]="wrong"
        self.assertFalse(approval_gate(self.plan,a,100)["approval_valid"])
    def test_rollback(self):
        a=self.approved();a["rollback_tested"]=False
        self.assertFalse(approval_gate(self.plan,a,100)["approval_valid"])
    def test_no_mutation_even_approved(self):self.assertEqual(approval_gate(self.plan,self.approved(),100,False)["mutations"],0)
    def test_no_network(self):self.assertEqual(demo()["network_calls"],0)
    def test_no_secret_values(self):self.assertEqual(demo()["secret_values_accessed"],0)
    def test_cli(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(out.getvalue())["mutations"],0)
if __name__=="__main__":unittest.main()
