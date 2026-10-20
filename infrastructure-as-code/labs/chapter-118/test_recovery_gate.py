import unittest
from dataclasses import replace
from recovery_gate import DrillEvidence,assess

class RecoveryGateTests(unittest.TestCase):
    def setUp(self):
        self.e=DrillEvidence("DR-118","stage","team-a","team-a","pod_termination",
            "pod_termination",240,300,15,60,True,True,True,True,True,True,
            True,True,True,True,True,True,False,False)
    def test_ready(self):
        self.assertEqual(assess(self.e)["decision"],"REVIEW_READY")
        self.assertEqual(assess(self.e)["score"],100)
    def test_mandatory_failures(self):
        for key in ("blast_radius","abort_controls","baseline_slos","failure_observability",
                    "state_restore","identity_and_policy","data_integrity"):
            with self.subTest(key=key):
                self.assertEqual(assess(replace(self.e,**{key:False}))["decision"],"NO_GO")
    def test_rto_breach(self):
        self.assertIn("rto_met",assess(replace(self.e,measured_rto_seconds=301))["failed_controls"])
    def test_rpo_breach(self):
        self.assertIn("rpo_met",assess(replace(self.e,measured_rpo_seconds=61))["failed_controls"])
    def test_fault_binding(self):
        self.assertIn("fault_binding",assess(replace(self.e,proposed_fault="region_failure"))["failed_controls"])
    def test_tenant_isolation(self):
        self.assertIn("tenant_scope",assess(replace(self.e,authorized_tenant="team-b"))["failed_controls"])
    def test_prod_denied(self):
        self.assertEqual(assess(replace(self.e,environment="prod"))["decision"],"NO_GO")
    def test_kill_switch(self):
        self.assertIn("kill_switch",assess(replace(self.e,kill_switch_active=True))["failed_controls"])
    def test_approvals(self):
        for key in ("sre_approved","security_approved","dbre_approved"):
            self.assertEqual(assess(replace(self.e,**{key:False}))["decision"],"NO_GO")
    def test_invalid_rpo(self):
        with self.assertRaises(ValueError):
            assess(replace(self.e,target_rpo_seconds=0))
if __name__=="__main__":
    unittest.main()
