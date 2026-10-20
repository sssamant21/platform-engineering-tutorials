import unittest
from dataclasses import replace
from deployment_gate import DeploymentEvidence,assess

class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.e=DeploymentEvidence("CHG-117","prod","team-a","team-a",
          "sha256:abc","sha256:abc","requester","approver",
          "2026-11-01T00:00:00Z","2026-10-20T12:00:00Z",
          True,True,True,True,True,True,True,True,True,True,
          True,True,True,True,False)
    def test_ready(self):
        self.assertEqual(assess(self.e)["decision"],"REVIEW_READY")
        self.assertEqual(assess(self.e)["score"],100)
    def test_mandatory_controls(self):
        for name in ("identity_scope","tenant_isolation","plan_integrity",
          "policy_passed","dependency_ready","approval_bound",
          "observability_ready","rollback_rehearsed","slo_healthy",
          "database_recovery_ready"):
            with self.subTest(name=name):
                self.assertEqual(assess(replace(self.e,**{name:False}))["decision"],"NO_GO")
    def test_binding(self):
        for changes in ({"approved_tenant":"team-b"},{"approved_plan_digest":"sha256:other"},
                        {"approver":"requester"},{"approval_expiry":"2026-10-19T00:00:00Z"}):
            with self.subTest(changes=changes):
                self.assertEqual(assess(replace(self.e,**changes))["decision"],"NO_GO")
    def test_approvals(self):
        for name in ("dbre_approved","security_approved","sre_approved"):
            self.assertEqual(assess(replace(self.e,**{name:False}))["decision"],"NO_GO")
    def test_exception(self):
        self.assertIn("critical_exception",assess(replace(self.e,critical_exception_open=True))["failed_controls"])
    def test_no_database(self):
        e=replace(self.e,database_in_scope=False,dbre_approved=False,database_recovery_ready=False)
        self.assertEqual(assess(e)["decision"],"REVIEW_READY")
    def test_naive_time(self):
        with self.assertRaises(ValueError):
            assess(replace(self.e,checked_at="2026-10-20T12:00:00"))
if __name__=="__main__":
    unittest.main()
