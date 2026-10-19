import unittest
from orchestrator import Rollout, ORDER

class RolloutTests(unittest.TestCase):
    def test_happy_path(self):
        r = Rollout()
        for s in ORDER:r.advance(s)
        self.assertEqual(tuple(r.completed), ORDER)
    def test_skip_preview(self):
        r = Rollout()
        with self.assertRaises(ValueError):r.advance("approve")
    def test_failed_validate(self):
        r = Rollout()
        with self.assertRaises(PermissionError):r.advance("validate", False)
    def test_stopped_cannot_resume(self):
        r = Rollout()
        with self.assertRaises(PermissionError):r.advance("validate", False)
        with self.assertRaises(RuntimeError):r.advance("validate")
    def test_missing_backup(self):
        r = Rollout()
        for s in ORDER[:3]:r.advance(s)
        with self.assertRaises(PermissionError):r.advance("backup", False)
    def test_canary_failure(self):
        r = Rollout()
        for s in ORDER[:4]:r.advance(s)
        with self.assertRaises(PermissionError):r.advance("canary", False)
    def test_health_failure(self):
        r = Rollout()
        for s in ORDER[:5]:r.advance(s)
        with self.assertRaises(PermissionError):r.advance("health", False)
    def test_missing_audit(self):
        r = Rollout()
        for s in ORDER[:7]:r.advance(s)
        with self.assertRaises(PermissionError):r.advance("audit", False)
    def test_repeated_stage(self):
        r = Rollout()
        r.advance("validate")
        with self.assertRaises(ValueError):r.advance("validate")
if __name__ == "__main__":
    unittest.main()
