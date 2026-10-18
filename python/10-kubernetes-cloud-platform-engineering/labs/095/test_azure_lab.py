import json,unittest
from contextlib import redirect_stdout
from io import StringIO
from azure_lab import Scope,LabError,pages,inventory,observation,pressure,cost_proxy,Plan,gate,FakePager,demo,main

class Tests(unittest.TestCase):
    def setUp(self):
        self.s=Scope("11111111-2222-3333-4444-555555555555","sre-staging")
        self.r=f"/subscriptions/{self.s.subscription}/resourceGroups/{self.s.resource_group}/providers/Microsoft.Compute/virtualMachines/vm01"
        self.p=Plan(self.s,self.r,"review-capacity","INC-095")
    def test_scope(self):self.s.validate()
    def test_bad_subscription(self):
        with self.assertRaises(LabError):Scope("bad","rg").validate()
    def test_bad_rg(self):
        with self.assertRaises(LabError):Scope(self.s.subscription,"../prod").validate()
    def test_pages(self):self.assertEqual(pages(FakePager([1,2,3],1).fetch),[1,2,3])
    def test_empty(self):self.assertEqual(pages(FakePager([]).fetch),[])
    def test_page_budget(self):
        with self.assertRaises(LabError):pages(FakePager([1,2,3],1).fetch,max_pages=2)
    def test_item_budget(self):
        with self.assertRaises(LabError):pages(FakePager([1,2,3],1).fetch,max_items=2)
    def test_page_loop(self):
        with self.assertRaises(LabError):pages(lambda token:{"items":[],"next":"loop"})
    def test_malformed(self):
        with self.assertRaises(LabError):pages(lambda token:{"items":None})
    def test_bad_page_budget(self):
        with self.assertRaises(LabError):pages(FakePager([]).fetch,max_pages=0)
    def test_inventory(self):
        self.assertEqual(inventory(self.s,vms=[{"id":self.r,"state":"Succeeded"}])["total"],1)
    def test_wrong_subscription(self):
        with self.assertRaises(LabError):inventory(self.s,vms=[{"id":"/subscriptions/other/vm","state":"Succeeded"}])
    def test_duplicate(self):
        x={"id":self.r,"state":"Succeeded"}
        with self.assertRaises(LabError):inventory(self.s,vms=[x,x])
    def test_missing_state(self):
        with self.assertRaises(LabError):inventory(self.s,vms=[{"id":self.r}])
    def test_inventory_budget(self):
        with self.assertRaises(LabError):inventory(self.s,max_items=0)
    def test_fresh(self):self.assertTrue(observation(10,950,1000)["fresh"])
    def test_stale(self):
        with self.assertRaises(LabError):observation(10,600,1000)
    def test_future(self):
        with self.assertRaises(LabError):observation(10,1001,1000)
    def test_nan(self):
        with self.assertRaises(LabError):observation(float("nan"),950,1000)
    def test_negative(self):
        with self.assertRaises(LabError):observation(-1,950,1000)
    def test_capacity_ok(self):self.assertFalse(pressure(40,60)["cpu_pressure"])
    def test_capacity_alert(self):self.assertTrue(pressure(92,8)["storage_pressure"])
    def test_bad_capacity(self):
        with self.assertRaises(LabError):pressure(110,20)
    def test_cost(self):self.assertEqual(cost_proxy(.25,24,2),12)
    def test_cost_negative(self):
        with self.assertRaises(LabError):cost_proxy(-1,24,1)
    def test_digest(self):self.assertEqual(len(self.p.digest()),64)
    def test_destructive_action(self):
        with self.assertRaises(LabError):Plan(self.s,self.r,"delete-vm","INC").digest()
    def test_cross_rg(self):
        with self.assertRaises(LabError):Plan(self.s,self.r.replace("sre-staging","prod"),"review-capacity","INC").digest()
    def test_gate_default(self):self.assertEqual(gate(self.p)["action"],"hold")
    def test_gate_approved(self):
        a={"approved":True,"digest":self.p.digest(),"rollback_tested":True,"owner":"oncall"}
        self.assertEqual(gate(self.p,a)["action"],"advisory-only")
    def test_wrong_digest(self):
        a={"approved":True,"digest":"wrong","rollback_tested":True,"owner":"oncall"}
        self.assertFalse(gate(self.p,a)["approved"])
    def test_missing_rollback(self):
        a={"approved":True,"digest":self.p.digest(),"rollback_tested":False,"owner":"oncall"}
        self.assertFalse(gate(self.p,a)["approved"])
    def test_zero_mutations(self):self.assertEqual(gate(self.p,dry_run=False)["mutations"],0)
    def test_demo(self):self.assertEqual(demo()["network_calls"],0)
    def test_demo_pressure(self):self.assertTrue(demo(True)["capacity"]["cpu_pressure"])
    def test_cli(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(out.getvalue())["mutations"],0)

if __name__=="__main__":unittest.main()
