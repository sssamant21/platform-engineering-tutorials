import unittest
from dataclasses import replace
from final_gate import FinalEvidence,assess

class FinalGateTests(unittest.TestCase):
    def setUp(self):
        self.e=FinalEvidence("FINAL-120","tenant-a","tenant-a","stage",
            True,True,True,True,True,True,True,True,True,True,True,True,
            True,True,True,True,True,0,0)
    def test_ready(self):
        self.assertEqual(assess(self.e)["decision"],"ELIGIBLE_FOR_INDEPENDENT_REVIEW")
        self.assertEqual(assess(self.e)["score"],100)
    def test_mandatory_controls(self):
        for key in ("identity_and_isolation","iac_state_and_drift",
                    "policy_and_supply_chain","observability_slos",
                    "incident_and_rollback","disaster_recovery","dbre_integrity"):
            with self.subTest(key=key):
                self.assertEqual(assess(replace(self.e,**{key:False}))["decision"],"NO_GO")
    def test_evidence_and_execution(self):
        for key in ("evidence_verified","labs_executed"):
            self.assertEqual(assess(replace(self.e,**{key:False}))["decision"],"NO_GO")
    def test_signoffs(self):
        for key in ("security_signoff","sre_signoff","dbre_signoff"):
            self.assertEqual(assess(replace(self.e,**{key:False}))["decision"],"NO_GO")
    def test_findings(self):
        for key in ("critical_findings","unapproved_high_findings"):
            self.assertEqual(assess(replace(self.e,**{key:1}))["decision"],"NO_GO")
    def test_tenant(self):
        self.assertIn("tenant_scope",assess(replace(self.e,authorized_tenant="tenant-b"))["failed_controls"])
    def test_no_database(self):
        e=replace(self.e,databases_in_scope=False,dbre_integrity=False,dbre_signoff=False)
        self.assertEqual(assess(e)["decision"],"ELIGIBLE_FOR_INDEPENDENT_REVIEW")
    def test_low_score(self):
        e=replace(self.e,architecture=False,delivery_and_gitops=False)
        self.assertEqual(assess(e)["decision"],"NO_GO")
    def test_invalid_findings(self):
        with self.assertRaises(ValueError):
            assess(replace(self.e,critical_findings=-1))
if __name__=="__main__":
    unittest.main()
