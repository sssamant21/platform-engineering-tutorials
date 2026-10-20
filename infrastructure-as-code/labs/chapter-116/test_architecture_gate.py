import unittest
from dataclasses import replace
from architecture_gate import ArchitectureEvidence,assess

class ArchitectureGateTests(unittest.TestCase):
    def setUp(self):
        self.e=ArchitectureEvidence("ARCH-116","prod",True,True,True,True,True,
            True,True,True,True,True,True,True,True,True,False)
    def test_full_acceptance(self):
        self.assertEqual(assess(self.e),{"decision":"REVIEW_READY","score":100,"failed_controls":[]})
    def test_mandatory_fail_closed(self):
        for field in ("tenant_isolation","identity_least_privilege","state_backup_and_locking",
                      "policy_and_supply_chain","observability_and_slos","recovery_drill","dbre_integrity"):
            with self.subTest(field=field):
                self.assertEqual(assess(replace(self.e,**{field:False}))["decision"],"NO_GO")
    def test_critical_exception(self):
        self.assertIn("critical_exception",assess(replace(self.e,critical_exception_open=True))["failed_controls"])
    def test_signoffs(self):
        for field in ("security_signoff","sre_signoff","dbre_signoff"):
            with self.subTest(field=field):
                self.assertEqual(assess(replace(self.e,**{field:False}))["decision"],"NO_GO")
    def test_low_score(self):
        e=replace(self.e,architecture_review=False,multi_cloud_boundaries=False)
        self.assertEqual(assess(e)["decision"],"NO_GO")
    def test_no_db_scope(self):
        e=replace(self.e,databases_in_scope=False,dbre_integrity=False,dbre_signoff=False)
        self.assertEqual(assess(e)["decision"],"REVIEW_READY")
    def test_invalid_environment(self):
        with self.assertRaises(ValueError):
            assess(replace(self.e,environment="unknown"))
if __name__=="__main__":
    unittest.main()
