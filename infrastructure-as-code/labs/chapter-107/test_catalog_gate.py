import unittest
from dataclasses import replace
from catalog_gate import CatalogRequest, validate

class CatalogGateTests(unittest.TestCase):
    def setUp(self):
        self.r = CatalogRequest("orders-api", "orders-team", "CC-100", "prod",
            "critical", "confidential", "v1.2.3", True, True, True, True,
            4000, 5000, True, True, True, True, 15, 60, True)
    def test_valid(self):
        self.assertEqual(validate(self.r)["decision"], "REVIEW_READY")
    def test_security_and_ownership(self):
        for field in ("authenticated","authorized","policy_passed","sre_approved",
                      "security_approved","dbre_approved","rollback_documented"):
            with self.subTest(field=field):
                self.assertEqual(validate(replace(self.r, **{field:False}))["decision"],"NO_GO")
    def test_budget(self):
        self.assertIn("budget",validate(replace(self.r,estimated_monthly_cost=9000))["failed"])
    def test_unpinned_template(self):
        self.assertIn("template_pinned",validate(replace(self.r,template_version="latest"))["failed"])
    def test_database_recovery(self):
        self.assertIn("recovery_contract",validate(replace(self.r,rpo_minutes=0))["failed"])
    def test_bad_name(self):
        self.assertIn("service_name",validate(replace(self.r,service="Bad Name"))["failed"])
    def test_negative_cost(self):
        with self.assertRaises(ValueError):
            validate(replace(self.r,approved_budget=-1))
if __name__ == "__main__":
    unittest.main()
