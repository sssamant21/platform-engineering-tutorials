import json,unittest
from contextlib import redirect_stdout
from io import StringIO
from gcp_lab import Scope,LabError,paginate,inventory,metric,capacity,cost_proxy,Plan,gate,FakePager,demo,main

class Tests(unittest.TestCase):
    def setUp(self):
        self.s=Scope("sre-lab-12345","us-central1-a")
        self.p=Plan(self.s,"vm1","review-capacity","INC-096")
    def test_scope(self):self.s.validate()
    def test_region(self):Scope("sre-lab-12345","us-central1").validate()
    def test_bad_project(self):
        with self.assertRaises(LabError):Scope("../prod","us-central1-a").validate()
    def test_bad_location(self):
        with self.assertRaises(LabError):Scope("sre-lab-12345","../zone").validate()
    def test_pages(self):self.assertEqual(paginate(FakePager([1,2,3],1).fetch),[1,2,3])
    def test_empty(self):self.assertEqual(paginate(FakePager([]).fetch),[])
    def test_page_budget(self):
        with self.assertRaises(LabError):paginate(FakePager([1,2,3],1).fetch,max_pages=2)
    def test_item_budget(self):
        with self.assertRaises(LabError):paginate(FakePager([1,2,3],1).fetch,max_items=2)
    def test_page_loop(self):
        with self.assertRaises(LabError):paginate(lambda token:{"items":[],"next_page_token":"same"})
    def test_bad_page(self):
        with self.assertRaises(LabError):paginate(lambda token:{"items":None})
    def test_bad_budget(self):
        with self.assertRaises(LabError):paginate(FakePager([]).fetch,max_pages=0)
    def test_inventory(self):
        self.assertEqual(inventory(self.s,compute=[{"name":"vm1","status":"RUNNING"}])["total"],1)
    def test_duplicate(self):
        x={"name":"vm1","status":"RUNNING"}
        with self.assertRaises(LabError):inventory(self.s,compute=[x,x])
    def test_missing_name(self):
        with self.assertRaises(LabError):inventory(self.s,compute=[{"status":"RUNNING"}])
    def test_missing_status(self):
        with self.assertRaises(LabError):inventory(self.s,compute=[{"name":"vm1"}])
    def test_inventory_budget(self):
        with self.assertRaises(LabError):inventory(self.s,max_items=0)
    def test_metric_fresh(self):self.assertTrue(metric(30,950,1000)["fresh"])
    def test_metric_stale(self):
        with self.assertRaises(LabError):metric(30,600,1000)
    def test_metric_future(self):
        with self.assertRaises(LabError):metric(30,1001,1000)
    def test_metric_nan(self):
        with self.assertRaises(LabError):metric(float("nan"),950,1000)
    def test_metric_negative(self):
        with self.assertRaises(LabError):metric(-1,950,1000)
    def test_capacity_ok(self):self.assertFalse(capacity(30,60)["cpu_pressure"])
    def test_capacity_alert(self):self.assertTrue(capacity(92,8)["storage_pressure"])
    def test_bad_capacity(self):
        with self.assertRaises(LabError):capacity(110,10)
    def test_cost(self):self.assertEqual(cost_proxy(.3,24,2),14.4)
    def test_negative_cost(self):
        with self.assertRaises(LabError):cost_proxy(-1,24,2)
    def test_digest(self):self.assertEqual(len(self.p.digest()),64)
    def test_destructive(self):
        with self.assertRaises(LabError):Plan(self.s,"vm1","delete-vm","INC").digest()
    def test_gate_hold(self):self.assertEqual(gate(self.p)["action"],"hold")
    def test_gate_approved(self):
        a={"approved":True,"digest":self.p.digest(),"rollback_tested":True,"owner":"oncall"}
        self.assertEqual(gate(self.p,a)["action"],"advisory-only")
    def test_wrong_digest(self):
        a={"approved":True,"digest":"wrong","rollback_tested":True,"owner":"oncall"}
        self.assertFalse(gate(self.p,a)["approved"])
    def test_rollback_missing(self):
        a={"approved":True,"digest":self.p.digest(),"rollback_tested":False,"owner":"oncall"}
        self.assertFalse(gate(self.p,a)["approved"])
    def test_no_mutations(self):self.assertEqual(gate(self.p,dry_run=False)["mutations"],0)
    def test_demo(self):self.assertEqual(demo()["network_calls"],0)
    def test_pressure_demo(self):self.assertTrue(demo(True)["capacity"]["cpu_pressure"])
    def test_cli(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(out.getvalue())["mutations"],0)

if __name__=="__main__":unittest.main()
