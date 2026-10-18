"""Deterministic offline tests for AWS-shaped SRE/DBRE inventory lab."""
import json,unittest
from contextlib import redirect_stdout
from io import StringIO
from aws_lab import Scope,LabError,paginate,inventory,metric,capacity,cost_proxy,Change,approve,FakePages,demo,main
class Tests(unittest.TestCase):
    def setUp(self):
        self.scope=Scope("123456789012","us-east-1")
        self.change=Change(self.scope,"db1","review-capacity","INC-094")
    def test_scope(self):self.scope.validate()
    def test_gov_region(self):Scope("123456789012","us-gov-west-1").validate()
    def test_bad_account(self):
        with self.assertRaises(LabError):Scope("abc","us-east-1").validate()
    def test_bad_region(self):
        with self.assertRaises(LabError):Scope("123456789012","../prod").validate()
    def test_pagination(self):self.assertEqual(len(paginate(FakePages([1,2,3],1).fetch)),3)
    def test_empty_pages(self):self.assertEqual(paginate(FakePages([]).fetch),[])
    def test_page_budget(self):
        with self.assertRaises(LabError):paginate(FakePages([1,2,3],1).fetch,max_pages=2)
    def test_item_budget(self):
        with self.assertRaises(LabError):paginate(FakePages([1,2,3],1).fetch,max_items=2)
    def test_loop(self):
        with self.assertRaises(LabError):paginate(lambda token:{"items":[],"next_token":"same"})
    def test_malformed(self):
        with self.assertRaises(LabError):paginate(lambda token:{"items":None})
    def test_bad_budget(self):
        with self.assertRaises(LabError):paginate(FakePages([]).fetch,max_pages=0)
    def test_inventory(self):
        r=inventory(self.scope,[{"id":"i-1","status":"running"}],[],[])
        self.assertEqual(r["total"],1)
    def test_duplicate(self):
        row={"id":"i-1","status":"running"}
        with self.assertRaises(LabError):inventory(self.scope,[row,row],[],[])
    def test_missing_record(self):
        with self.assertRaises(LabError):inventory(self.scope,[{"id":"i-1"}],[],[])
    def test_inventory_budget(self):
        with self.assertRaises(LabError):inventory(self.scope,[{"id":"i-1","status":"running"}],[],[],max_resources=0)
    def test_metric_fresh(self):self.assertTrue(metric(20,950,1000)["fresh"])
    def test_metric_stale(self):
        with self.assertRaises(LabError):metric(20,600,1000)
    def test_metric_future(self):
        with self.assertRaises(LabError):metric(20,1001,1000)
    def test_metric_nan(self):
        with self.assertRaises(LabError):metric(float("nan"),950,1000)
    def test_metric_negative(self):
        with self.assertRaises(LabError):metric(-1,950,1000)
    def test_capacity_normal(self):self.assertFalse(capacity(40,100)["cpu_pressure"])
    def test_capacity_pressure(self):self.assertTrue(capacity(90,10)["storage_pressure"])
    def test_capacity_bad(self):
        with self.assertRaises(LabError):capacity(120,10)
    def test_cost(self):self.assertEqual(cost_proxy(.2,24,2),9.6)
    def test_cost_bad(self):
        with self.assertRaises(LabError):cost_proxy(-1,24,2)
    def test_change_digest(self):self.assertEqual(len(self.change.digest()),64)
    def test_change_action(self):
        with self.assertRaises(LabError):Change(self.scope,"db1","delete-db","INC-094").digest()
    def test_dry_run(self):self.assertEqual(approve(self.change)["mutations"],0)
    def test_unapproved(self):self.assertEqual(approve(self.change)["action"],"hold")
    def test_approved(self):
        a={"approved":True,"digest":self.change.digest(),"rollback_tested":True,"owner":"oncall"}
        self.assertEqual(approve(self.change,a)["action"],"advisory-only")
    def test_wrong_digest(self):
        a={"approved":True,"digest":"bad","rollback_tested":True,"owner":"oncall"}
        self.assertFalse(approve(self.change,a)["approved"])
    def test_rollback_missing(self):
        a={"approved":True,"digest":self.change.digest(),"rollback_tested":False,"owner":"oncall"}
        self.assertFalse(approve(self.change,a)["approved"])
    def test_demo(self):self.assertEqual(demo()["mutations"],0)
    def test_pressure_demo(self):self.assertTrue(demo(True)["capacity"]["cpu_pressure"])
    def test_cli(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(out.getvalue())["network_calls"],0)
if __name__=="__main__":unittest.main()
