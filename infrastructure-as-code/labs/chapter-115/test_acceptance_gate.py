import unittest
from dataclasses import replace
from acceptance_gate import Evidence,assess

class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.e=Evidence("CHG-115","team-a","prod",True,True,True,True,
            True,True,True,True,True,True,True,True,True,True,True,False)
    def test_pass(self):
        self.assertEqual(assess(self.e)["decision"],"REVIEW_READY")
        self.assertEqual(assess(self.e)["score"],100)
    def test_mandatory_failures(self):
        for key in ("event_authentication","replay_and_idempotency","tenant_isolation",
                    "least_privilege","deterministic_policy","human_approval_binding",
                    "kill_switch_tested","audit_complete","rollback_rehearsed",
                    "slo_validation","dbre_recovery_evidence"):
            with self.subTest(key=key):
                self.assertEqual(assess(replace(self.e,**{key:False}))["decision"],"NO_GO")
    def test_approvals(self):
        for key in ("security_approved","sre_approved","dbre_approved"):
            with self.subTest(key=key):
                self.assertEqual(assess(replace(self.e,**{key:False}))["decision"],"NO_GO")
    def test_ai_injection(self):
        self.assertIn("unsafe_ai_instruction",assess(replace(self.e,
            unsafe_ai_instruction_detected=True))["failed_controls"])
    def test_database_out_of_scope(self):
        e=replace(self.e,database_in_scope=False,dbre_approved=False,
            dbre_recovery_evidence=False)
        self.assertEqual(assess(e)["decision"],"REVIEW_READY")
    def test_invalid_identity(self):
        with self.assertRaises(ValueError):
            assess(replace(self.e,tenant=" "))
if __name__=="__main__":
    unittest.main()
