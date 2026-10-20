import unittest
from dataclasses import replace
from platform_gate import PlatformRequest, evaluate

class GoldenPathGateTests(unittest.TestCase):
    def setUp(self):
        self.valid = PlatformRequest(
            "checkout", "payments-api", "stage", "us-east-1", "critical",
            True, True, True, True, True, True, True,
            5000, True, True, True, True)
    def test_valid(self):
        self.assertEqual(evaluate(self.valid)["decision"], "REVIEW_READY")
    def test_invalid_region(self):
        self.assertIn("region", evaluate(replace(self.valid, region="unknown"))["failed_controls"])
    def test_production_security_controls(self):
        for field in ("module_version_pinned", "workload_identity_enabled",
                      "secrets_externalized", "state_encrypted", "state_locked",
                      "policy_checks_passed", "plan_reviewed", "budget_approved",
                      "sre_approved"):
            with self.subTest(field=field):
                self.assertEqual(evaluate(replace(self.valid, **{field:False}))["decision"], "NO_GO")
    def test_database_approval(self):
        self.assertIn("dbre_approval", evaluate(replace(self.valid, dbre_approved=False))["failed_controls"])
        self.assertEqual(evaluate(replace(self.valid, contains_database=False, dbre_approved=False))["decision"], "REVIEW_READY")
    def test_budget_cap(self):
        self.assertIn("budget", evaluate(replace(self.valid, cost_estimate_usd=100001))["failed_controls"])
    def test_negative_cost(self):
        with self.assertRaises(ValueError):
            evaluate(replace(self.valid, cost_estimate_usd=-1))
    def test_blank_service(self):
        with self.assertRaises(ValueError):
            evaluate(replace(self.valid, service=" "))
if __name__ == "__main__":
    unittest.main()
