import unittest
from dataclasses import replace
from governance_gate import ChangeRequest,evaluate

class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.e=ChangeRequest("CHG-114","team-a","team-a","prod","retry_readonly_plan",
            "alice","bob","retry_readonly_plan","sha256:abc","sha256:abc",
            "2026-10-21T12:00:00Z","2026-10-20T12:00:00Z",
            False,"",False,True,True,True,True,True,True,False,False,False,False,True)
    def test_valid(self):
        self.assertEqual(evaluate(self.e)["decision"],"REVIEW_READY")
    def test_cross_tenant(self):
        self.assertIn("tenant_scope",evaluate(replace(self.e,authorized_tenant="team-b"))["failed_controls"])
    def test_separation_of_duties(self):
        self.assertIn("separation_of_duties",evaluate(replace(self.e,approver="alice"))["failed_controls"])
    def test_expired_approval(self):
        self.assertIn("approval_not_expired",evaluate(replace(self.e,approval_expires_at="2026-10-19T12:00:00Z"))["failed_controls"])
    def test_plan_mismatch(self):
        self.assertIn("plan_binding",evaluate(replace(self.e,submitted_plan_hash="sha256:other"))["failed_controls"])
    def test_kill_switch(self):
        self.assertIn("kill_switch",evaluate(replace(self.e,kill_switch_enabled=True))["failed_controls"])
    def test_unsafe_action(self):
        self.assertIn("action_allowlist",evaluate(replace(self.e,action="terraform_destroy"))["failed_controls"])
    def test_critical_controls(self):
        for field in ("policy_healthy","audit_healthy","identity_verified",
                      "dry_run_passed","rollback_verified","scope_limited","sre_approved"):
            with self.subTest(field=field):
                self.assertEqual(evaluate(replace(self.e,**{field:False}))["decision"],"NO_GO")
    def test_database_review(self):
        self.assertIn("dbre",evaluate(replace(self.e,database_affected=True))["failed_controls"])
    def test_security_review(self):
        self.assertIn("security",evaluate(replace(self.e,security_affected=True))["failed_controls"])
    def test_break_glass(self):
        self.assertIn("break_glass",evaluate(replace(self.e,emergency=True))["failed_controls"])
    def test_timezone_required(self):
        with self.assertRaises(ValueError):
            evaluate(replace(self.e,evaluation_time="2026-10-20T12:00:00"))
if __name__=="__main__":
    unittest.main()
