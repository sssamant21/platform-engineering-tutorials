import unittest
from dataclasses import replace
from tenant_gate import AccessRequest, authorize

class TenantGateTests(unittest.TestCase):
    def setUp(self):
        self.r=AccessRequest("ci-orders","orders","orders","prod","apply",
            "operator",True,True,True,True,True,True,True,False,False,0)
    def test_valid(self):
        self.assertEqual(authorize(self.r)["decision"],"REVIEW_READY")
    def test_cross_tenant(self):
        self.assertIn("tenant_isolation",authorize(replace(self.r,resource_tenant="billing"))["failed"])
    def test_production_approvals(self):
        for field in ("workload_identity","policy_passed","approval_bound_to_plan",
                      "change_approved","security_approved","dbre_approved"):
            with self.subTest(field=field):
                self.assertEqual(authorize(replace(self.r,**{field:False}))["decision"],"DENY")
    def test_reader_cannot_apply(self):
        self.assertIn("role_scope",authorize(replace(self.r,role="reader"))["failed"])
    def test_destroy_requires_admin(self):
        self.assertIn("role_scope",authorize(replace(self.r,action="destroy"))["failed"])
    def test_break_glass_expires(self):
        self.assertIn("break_glass",authorize(replace(self.r,emergency_access=True,
            emergency_ticket_valid=True,emergency_expires_in_minutes=61))["failed"])
    def test_emergency_does_not_override_tenant(self):
        self.assertIn("tenant_isolation",authorize(replace(self.r,resource_tenant="billing",
            emergency_access=True,emergency_ticket_valid=True,emergency_expires_in_minutes=30))["failed"])
    def test_invalid_ttl(self):
        with self.assertRaises(ValueError):
            authorize(replace(self.r,emergency_expires_in_minutes=-1))
if __name__=="__main__":
    unittest.main()
