import unittest
from dataclasses import replace
from platform_acceptance import PlatformAcceptance, assess

class PlatformAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.e = PlatformAcceptance("enterprise-platform",
            True, True, True, True, True, True, True, True,
            True, True, True, True, True, True, True)
    def test_valid(self):
        self.assertEqual(assess(self.e)["score"], 100)
        self.assertEqual(assess(self.e)["decision"], "REVIEW_READY")
    def test_mandatory_controls(self):
        for name in ("catalog_ownership", "tenant_isolation",
                     "identity_least_privilege", "policy_enforced",
                     "plan_hash_approved", "state_restore_verified",
                     "kubernetes_slo_verified", "audit_complete",
                     "database_recovery_verified"):
            with self.subTest(control=name):
                self.assertEqual(assess(replace(self.e, **{name: False}))["decision"], "NO_GO")
    def test_signatures(self):
        for name in ("security_signed", "sre_signed", "dbre_signed"):
            with self.subTest(signature=name):
                self.assertEqual(assess(replace(self.e, **{name: False}))["decision"], "NO_GO")
    def test_database_out_of_scope(self):
        self.assertEqual(assess(replace(self.e,database_in_scope=False,
            dbre_signed=False,database_recovery_verified=False))["decision"],"REVIEW_READY")
    def test_threshold(self):
        e=replace(self.e,golden_path_versioned=False,incident_rehearsed=False)
        self.assertEqual(assess(e)["score"],85)
        self.assertEqual(assess(e)["decision"],"NO_GO")
    def test_missing_platform(self):
        with self.assertRaises(ValueError):
            assess(replace(self.e,platform=" "))
if __name__=="__main__":
    unittest.main()
