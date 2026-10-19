import unittest
from dataclasses import replace
from failover_gate import FailoverEvidence, decide

class FailoverTests(unittest.TestCase):
    def setUp(self):
        self.safe = FailoverEvidence(True,True,4,15,True,True,True,True,True,True,True)
    def test_ready(self):
        self.assertEqual(decide(self.safe)["decision"],"REHEARSAL_READY")
    def test_each_control_fail_closed(self):
        for field in ("primary_fenced","quorum_verified","backup_restorable",
                      "recovery_keys_ready","target_capacity_ready","dns_ready",
                      "incident_commander_approved","dbre_approved","rollback_plan_ready"):
            with self.subTest(field=field):
                self.assertEqual(decide(replace(self.safe,**{field:False}))["decision"],"BLOCK")
    def test_lag(self):
        self.assertIn("lag",decide(replace(self.safe,replica_lag_seconds=30))["failed"])
    def test_negative_lag(self):
        with self.assertRaises(ValueError):
            decide(replace(self.safe,replica_lag_seconds=-1))
if __name__=="__main__":
    unittest.main()
