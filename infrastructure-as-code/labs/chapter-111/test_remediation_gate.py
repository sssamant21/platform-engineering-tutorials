import unittest
from dataclasses import replace
from remediation_gate import Remediation,evaluate

class GateTests(unittest.TestCase):
    def setUp(self):
        self.r=Remediation("INC-123","retry_idempotent_plan","stage","team-a",
            "team-a",True,True,True,True,True,True,True,True,
            1,99,False,False,False,False,False)
    def test_allowed(self):
        self.assertEqual(evaluate(self.r)["decision"],"REVIEW_READY")
    def test_cross_tenant(self):
        self.assertIn("tenant_scope",evaluate(replace(self.r,tenant="team-b"))["failed_controls"])
    def test_disallowed_action(self):
        self.assertIn("action_allowlist",evaluate(replace(self.r,action="terraform_apply"))["failed_controls"])
    def test_all_guards_fail_closed(self):
        for f in ("idempotent","preapproved","policy_passed","dry_run_passed",
                  "change_window_open","rollback_available","audit_sink_healthy",
                  "state_lock_clear"):
            with self.subTest(f=f):
                self.assertEqual(evaluate(replace(self.r,**{f:False}))["decision"],"NO_GO")
    def test_production_needs_human(self):
        self.assertIn("production_human",evaluate(replace(self.r,environment="prod"))["failed_controls"])
    def test_database_needs_dbre(self):
        self.assertIn("database_human",evaluate(replace(self.r,database_affected=True,human_approved=True))["failed_controls"])
    def test_security_needs_review(self):
        self.assertIn("security_human",evaluate(replace(self.r,security_affected=True,human_approved=True))["failed_controls"])
    def test_invalid_confidence(self):
        with self.assertRaises(ValueError):
            evaluate(replace(self.r,confidence_percent=101))
    def test_blast_radius(self):
        self.assertIn("blast_radius",evaluate(replace(self.r,blast_radius_resources=4))["failed_controls"])
if __name__=="__main__":
    unittest.main()
