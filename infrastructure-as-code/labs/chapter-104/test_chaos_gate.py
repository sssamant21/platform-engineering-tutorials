import unittest
from dataclasses import replace
from chaos_gate import DrillEvidence, assess

class ChaosGateTests(unittest.TestCase):
    def setUp(self):
        self.good=DrillEvidence("orders","one staging namespace",True,True,
            True,True,True,True,True,True,60,300,240,900,True,True)
    def test_valid(self):
        self.assertEqual(assess(self.good)["decision"],"REVIEW_READY")
    def test_boolean_gates_fail_closed(self):
        fields=("authorized","staging_only","stop_switch_verified","baseline_slo_ok",
                "fault_observed","recovery_verified","data_integrity_verified",
                "rollback_verified","dbre_approved","sre_approved")
        for field in fields:
            with self.subTest(field=field):
                self.assertEqual(assess(replace(self.good,**{field:False}))["decision"],"NO_GO")
    def test_rpo_breach(self):
        self.assertIn("rpo",assess(replace(self.good,rpo_observed_seconds=400))["failed"])
    def test_rto_breach(self):
        self.assertIn("rto",assess(replace(self.good,rto_observed_seconds=1000))["failed"])
    def test_negative_time(self):
        with self.assertRaises(ValueError):
            assess(replace(self.good,rto_target_seconds=-1))
    def test_missing_scope(self):
        with self.assertRaises(ValueError):
            assess(replace(self.good,blast_radius=""))
if __name__=="__main__":
    unittest.main()
