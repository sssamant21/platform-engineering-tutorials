"""Chapter 090 offline SRE capstone tests (standard library only)."""
import json,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import redirect_stdout
from io import StringIO
from capstone import Resource,Metrics,Plan,PolicyError,inventory,slo,assess,apply_marker,fixtures,main

class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.root=Path(self.temp.name)
        self.now=1000.;self.rows,self.metrics,self.events,self.checks=fixtures(self.now)
        self.plan=Plan("INC-1001","postgres-health","manual-review")
    def tearDown(self):self.temp.cleanup()
    def report(self,**kw):
        return assess(self.rows,self.metrics,self.events,self.checks,"INC-1001","postgres-health",self.now,**kw)
    def apply(self,plan=None):
        p=plan or self.plan
        return apply_marker(p,self.root,apply=True,approval_digest=p.digest(),approver="oncall",expires=1200,now=self.now)
    def test_inventory(self):self.assertEqual(inventory(self.rows,"postgres-health")["total"],2)
    def test_unhealthy(self):self.assertEqual(inventory([Resource("postgres-health","pod","p",False)],"postgres-health")["unhealthy"],1)
    def test_bad_resource(self):
        with self.assertRaises(PolicyError):inventory([Resource("../x","pod","p",True)],"postgres-health")
    def test_inventory_budget(self):
        with self.assertRaises(PolicyError):inventory(self.rows,"postgres-health",1)
    def test_scope(self):
        with self.assertRaises(PolicyError):inventory(self.rows,"../prod")
    def test_metrics_valid(self):self.metrics.validate(self.now)
    def test_nan(self):
        with self.assertRaises(PolicyError):Metrics(float("nan"),1,1,990).validate(self.now)
    def test_negative(self):
        with self.assertRaises(PolicyError):Metrics(-1,1,1,990).validate(self.now)
    def test_stale(self):
        with self.assertRaises(PolicyError):Metrics(1,1,1,100).validate(self.now)
    def test_future(self):
        with self.assertRaises(PolicyError):Metrics(1,1,1,1001).validate(self.now)
    def test_slo(self):self.assertEqual(slo([True]*100)["availability"],1)
    def test_exhausted(self):self.assertTrue(slo([False]*10+[True]*90)["exhausted"])
    def test_burn(self):self.assertGreater(slo([False]*10+[True]*90)["burn_rate"],2)
    def test_no_traffic(self):self.assertIsNone(slo([])["availability"])
    def test_low_traffic(self):self.assertFalse(slo([True])["sufficient"])
    def test_bad_target(self):
        with self.assertRaises(PolicyError):slo([True],target=1)
    def test_bad_event(self):
        with self.assertRaises(PolicyError):slo([1,True])
    def test_ready(self):self.assertTrue(self.report()["readiness"]["ready"])
    def test_missing_owner(self):
        self.checks["owner_assigned"]=False
        self.assertFalse(self.report()["readiness"]["ready"])
    def test_missing_check(self):
        del self.checks["rollback_tested"]
        self.assertIn("missing-readiness-evidence",self.report()["readiness"]["reasons"])
    def test_sev1(self):self.assertIn("active-sev1",self.report(open_sev1=True)["readiness"]["reasons"])
    def test_no_inventory(self):
        self.rows=[]
        self.assertIn("missing-inventory",self.report()["readiness"]["reasons"])
    def test_unhealthy_gate(self):
        self.rows[0]=Resource("postgres-health","database","primary",False)
        self.assertIn("unhealthy-resource",self.report()["readiness"]["reasons"])
    def test_pressure(self):
        self.metrics=Metrics(95,40,40,990)
        self.assertIn("resource-pressure",self.report()["readiness"]["reasons"])
    def test_budget_gate(self):
        self.events=[False]*10+[True]*90
        self.assertIn("error-budget-exhausted",self.report()["readiness"]["reasons"])
    def test_burn_rationale(self):
        self.events=[False]*10+[True]*90
        self.assertEqual(self.report()["plan"]["rationale"],"slo-burn")
    def test_digest(self):self.assertEqual(len(self.plan.digest()),64)
    def test_action_allowlist(self):
        with self.assertRaises(PolicyError):Plan("INC-1001","postgres-health","manual-review","restart-db").validate()
    def test_dry_run(self):
        self.assertEqual(apply_marker(self.plan,self.root)["mutations"],0)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_no_approval(self):
        with self.assertRaises(PolicyError):apply_marker(self.plan,self.root,apply=True,now=self.now)
    def test_wrong_digest(self):
        with self.assertRaises(PolicyError):
            apply_marker(self.plan,self.root,apply=True,approval_digest="bad",approver="oncall",expires=1200,now=self.now)
    def test_expired(self):
        with self.assertRaises(PolicyError):
            apply_marker(self.plan,self.root,apply=True,approval_digest=self.plan.digest(),approver="oncall",expires=999,now=self.now)
    def test_apply(self):self.assertEqual(self.apply()["status"],"applied")
    def test_duplicate(self):
        self.apply()
        self.assertEqual(self.apply()["status"],"already-applied")
    def test_conflict(self):
        self.apply()
        with self.assertRaises(PolicyError):self.apply(Plan("INC-1001","postgres-health","resource-pressure"))
    def test_corrupt(self):
        self.apply()
        (self.root/"INC-1001-postgres-health.marker").write_text("corrupt")
        with self.assertRaises(PolicyError):self.apply()
    def test_audit(self):
        self.apply();self.apply()
        lines=[json.loads(x) for x in (self.root/"audit.jsonl").read_text().splitlines()]
        self.assertEqual([x["event"] for x in lines],["applied","duplicate"])
    def test_missing_root(self):
        with self.assertRaises(OSError):
            apply_marker(self.plan,self.root/"missing",apply=True,
                         approval_digest=self.plan.digest(),approver="oncall",expires=1200,now=self.now)
    def test_cli_dry(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(out.getvalue())["execution"]["mutations"],0)
    def test_cli_healthy(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--failures","0"]),0)
        self.assertTrue(json.loads(out.getvalue())["readiness"]["ready"])
    def test_cli_incident(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--failures","20","--pressure"]),0)
        self.assertFalse(json.loads(out.getvalue())["readiness"]["ready"])
    def test_cli_reject(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--apply"]),2)
        self.assertEqual(json.loads(out.getvalue())["status"],"rejected")
    def test_bad_fixture(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--failures","101"]),2)
if __name__=="__main__":unittest.main()
