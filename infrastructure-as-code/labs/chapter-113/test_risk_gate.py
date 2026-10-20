import unittest
from dataclasses import replace
from risk_gate import ChangeEvidence,assess

class RiskGateTests(unittest.TestCase):
    def setUp(self):
        self.e=ChangeEvidence("CHG-113","team-a","team-a","prod",2,0,0,
            55,65,True,True,True,True,True,True,True,True,True,True)
    def test_baseline(self):
        self.assertEqual(assess(self.e)["decision"],"REVIEW_READY")
    def test_tenant_isolation(self):
        self.assertIn("tenant_scope",assess(replace(self.e,authorized_tenant="team-b"))["failed_controls"])
    def test_destructive_change(self):
        self.assertIn("destructive_change",assess(replace(self.e,destructive_changes=1))["failed_controls"])
    def test_privileged_change(self):
        self.assertIn("privileged_change",assess(replace(self.e,privileged_changes=1))["failed_controls"])
    def test_capacity(self):
        self.assertIn("capacity",assess(replace(self.e,projected_capacity_utilization_pct=90))["failed_controls"])
    def test_fail_closed_controls(self):
        for field in ("telemetry_fresh","drift_plan_reviewed","policy_passed",
                      "plan_hash_approved","audit_available","rollback_tested",
                      "security_approved","sre_approved","dbre_approved"):
            with self.subTest(field=field):
                self.assertEqual(assess(replace(self.e,**{field:False}))["decision"],"NO_GO")
    def test_invalid_count(self):
        with self.assertRaises(ValueError):
            assess(replace(self.e,drift_resources=-1))
    def test_invalid_utilization(self):
        with self.assertRaises(ValueError):
            assess(replace(self.e,projected_capacity_utilization_pct=101))
if __name__=="__main__":
    unittest.main()
