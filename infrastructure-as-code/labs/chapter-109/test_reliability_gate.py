import unittest
from dataclasses import replace
from reliability_gate import ReliabilityEvidence, assess

class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.e=ReliabilityEvidence("iac-platform",30,100000,99980,99.9,
            90,120,12,100,55,80,True,True,True,True,True,True,True,True,True)
    def test_valid(self):
        self.assertEqual(assess(self.e)["decision"],"REVIEW_READY")
    def test_slo_breach(self):
        self.assertIn("availability",assess(replace(self.e,requests_successful=99000))["failed"])
    def test_latency_breach(self):
        self.assertIn("provision_latency",assess(replace(self.e,p95_provision_seconds=150))["failed"])
    def test_queue_and_capacity(self):
        self.assertEqual(assess(replace(self.e,queue_depth=101,runner_capacity_percent=90))["decision"],"NO_GO")
    def test_critical_controls(self):
        for f in ("state_backend_healthy","state_restore_tested","policy_engine_healthy",
                  "gitops_reconciliation_healthy","audit_events_complete",
                  "incident_runbook_tested","sre_approved","dbre_approved"):
            with self.subTest(field=f):
                self.assertEqual(assess(replace(self.e,**{f:False}))["decision"],"NO_GO")
    def test_no_database_requires_no_dbre_signoff(self):
        self.assertEqual(assess(replace(self.e,manages_databases=False,dbre_approved=False))["decision"],"REVIEW_READY")
    def test_invalid_counters(self):
        with self.assertRaises(ValueError):
            assess(replace(self.e,requests_successful=100001))
    def test_invalid_window(self):
        with self.assertRaises(ValueError):
            assess(replace(self.e,window_days=0))
if __name__=="__main__":
    unittest.main()
