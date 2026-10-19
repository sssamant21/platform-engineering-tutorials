import unittest
from dataclasses import replace
from dr_gate import RecoveryEvidence, evaluate

class DisasterRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.good = RecoveryEvidence(
            "orders-db", "tier-1", 15, 60,
            "2026-10-19T11:50:00Z", "2026-10-19T12:00:00Z",
            "2026-10-19T12:35:00Z",
            True, True, True, True, True, True)

    def test_valid_evidence(self):
        result = evaluate(self.good)
        self.assertEqual(result["decision"], "REVIEW_READY")
        self.assertEqual(result["observed_rpo_minutes"], 10)
        self.assertEqual(result["observed_rto_minutes"], 35)

    def test_rpo_breach(self):
        result = evaluate(replace(self.good, latest_recoverable_point="2026-10-19T11:30:00Z"))
        self.assertIn("rpo", result["failed_controls"])

    def test_rto_breach(self):
        result = evaluate(replace(self.good, service_restored="2026-10-19T13:30:00Z"))
        self.assertIn("rto", result["failed_controls"])

    def test_missing_controls_fail_closed(self):
        fields = ["backup_immutable", "restore_test_passed", "state_recoverable",
                  "secrets_recoverable", "region_independent", "owner_approved"]
        for field in fields:
            with self.subTest(field=field):
                result = evaluate(replace(self.good, **{field: False}))
                self.assertEqual(result["decision"], "NO_GO")

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(replace(self.good, outage_started="2026-10-19T12:00:00"))

    def test_future_backup_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(replace(self.good, latest_recoverable_point="2026-10-19T12:01:00Z"))

    def test_negative_rpo_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(replace(self.good, rpo_target_minutes=-1))

if __name__ == "__main__":
    unittest.main()
