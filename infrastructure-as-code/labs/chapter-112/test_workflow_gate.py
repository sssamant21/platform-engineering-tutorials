import unittest
from dataclasses import replace
from workflow_gate import WorkflowEvent,evaluate

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.e=WorkflowEvent("evt-1","INC-1","team-a","team-a","otel",
            "retry_readonly_plan","stage","approved","executing",
            True,True,True,True,True,True,True,True,3,1,False,False,False,False)
    def test_valid(self):
        self.assertEqual(evaluate(self.e)["decision"],"REVIEW_READY")
    def test_cross_tenant(self):
        self.assertIn("tenant_isolation",evaluate(replace(self.e,authorized_tenant="team-b"))["failed_controls"])
    def test_disallowed_apply(self):
        self.assertIn("action_allowlist",evaluate(replace(self.e,action="terraform_apply"))["failed_controls"])
    def test_replay(self):
        self.assertIn("replay_protection",evaluate(replace(self.e,replay_protected=False))["failed_controls"])
    def test_terminal_state(self):
        self.assertIn("state_transition",evaluate(replace(self.e,current_state="completed"))["failed_controls"])
    def test_retry_exhaustion(self):
        self.assertIn("retry_budget",evaluate(replace(self.e,attempted_retries=4))["failed_controls"])
    def test_controls(self):
        for field in ("signature_verified","idempotency_key_present","policy_passed",
                      "audit_available","approval_present","dry_run_passed","rollback_ready"):
            with self.subTest(field=field):
                self.assertEqual(evaluate(replace(self.e,**{field:False}))["decision"],"NO_GO")
    def test_dbre(self):
        self.assertIn("database_approval",evaluate(replace(self.e,database_affected=True))["failed_controls"])
    def test_security(self):
        self.assertIn("security_approval",evaluate(replace(self.e,security_affected=True))["failed_controls"])
    def test_invalid_retries(self):
        with self.assertRaises(ValueError):
            evaluate(replace(self.e,max_retries=-1))
if __name__=="__main__":
    unittest.main()
