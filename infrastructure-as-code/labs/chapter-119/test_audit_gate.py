import unittest
from dataclasses import replace
from audit_gate import AuditEvidence, assess

class AuditGateTests(unittest.TestCase):
    def setUp(self):
        self.e=AuditEvidence("AUD-119","prod","team-a","team-a",
            True,True,True,True,True,True,True,True,True,True,True,
            True,True,True,True,0,0,0)
    def test_baseline(self):
        self.assertEqual(assess(self.e),{"decision":"REVIEW_READY","score":100,"failed_controls":[]})
    def test_mandatory_controls(self):
        for field in ("identity_and_tenant_isolation","state_and_secrets_protection",
                      "supply_chain_and_policy","audit_and_compliance_evidence",
                      "recovery_drill","change_governance","dbre_integrity"):
            with self.subTest(field=field):
                self.assertEqual(assess(replace(self.e,**{field:False}))["decision"],"NO_GO")
    def test_stale_or_unverified_evidence(self):
        for field in ("evidence_current","evidence_provenance_verified"):
            self.assertEqual(assess(replace(self.e,**{field:False}))["decision"],"NO_GO")
    def test_cross_tenant(self):
        self.assertIn("tenant_scope",assess(replace(self.e,authorized_tenant="team-b"))["failed_controls"])
    def test_critical_finding(self):
        self.assertIn("critical_findings",assess(replace(self.e,critical_findings_open=1))["failed_controls"])
    def test_unapproved_high(self):
        self.assertIn("unapproved_high_findings",assess(replace(self.e,high_findings_open=1))["failed_controls"])
    def test_approved_high_exception(self):
        self.assertEqual(assess(replace(self.e,high_findings_open=1,approved_high_exceptions=1))["decision"],"REVIEW_READY")
    def test_approvals(self):
        for field in ("dbre_signoff","security_signoff","sre_signoff"):
            self.assertEqual(assess(replace(self.e,**{field:False}))["decision"],"NO_GO")
    def test_low_score(self):
        self.assertEqual(assess(replace(self.e,cost_allocation_and_budget=False,
                                        capacity_and_slo=False))["decision"],"NO_GO")
    def test_invalid_exception_count(self):
        with self.assertRaises(ValueError):
            assess(replace(self.e,approved_high_exceptions=2))
    def test_no_db_scope(self):
        e=replace(self.e,databases_in_scope=False,dbre_integrity=False,dbre_signoff=False)
        self.assertEqual(assess(e)["decision"],"REVIEW_READY")
if __name__=="__main__":
    unittest.main()
