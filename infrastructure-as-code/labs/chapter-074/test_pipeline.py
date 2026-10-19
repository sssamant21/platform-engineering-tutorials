import unittest
from pipeline_sim import Pipeline, ORDER

class PipelineTests(unittest.TestCase):
    def test_happy_path(self):
        p = Pipeline()
        for stage in ORDER:
            p.advance(stage)
        self.assertEqual(tuple(p.stages), ORDER)
    def test_wrong_order(self):
        p = Pipeline()
        with self.assertRaises(ValueError):
            p.advance("promote")
    def test_fail_closed(self):
        p = Pipeline()
        with self.assertRaises(PermissionError):
            p.advance("validate", allowed=False)
        with self.assertRaises(RuntimeError):
            p.advance("validate")
    def test_repeated_stage(self):
        p = Pipeline()
        p.advance("validate")
        with self.assertRaises(ValueError):
            p.advance("validate")
    def test_reject_canary(self):
        p = Pipeline()
        for stage in ORDER[:3]:
            p.advance(stage)
        with self.assertRaises(PermissionError):
            p.advance("canary", allowed=False)
    def test_reject_health(self):
        p = Pipeline()
        for stage in ORDER[:4]:
            p.advance(stage)
        with self.assertRaises(PermissionError):
            p.advance("health", allowed=False)
    def test_extra_stage(self):
        p = Pipeline()
        for stage in ORDER:
            p.advance(stage)
        with self.assertRaises(ValueError):
            p.advance("promote")
if __name__ == "__main__":
    unittest.main()
