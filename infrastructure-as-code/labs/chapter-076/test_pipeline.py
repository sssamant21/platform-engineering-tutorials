import unittest
from gate import STAGES
from pipeline import Delivery
class PipelineTests(unittest.TestCase):
    def test_happy_path(self):
        d=Delivery()
        for s in STAGES:d.advance(s)
        self.assertEqual(tuple(d.completed),STAGES)
    def test_skipped_lint(self):
        with self.assertRaises(ValueError):Delivery().advance('plan')
    def test_failed_lint(self):
        with self.assertRaises(PermissionError):Delivery().advance('lint',False)
    def test_halted_cannot_resume(self):
        d=Delivery()
        with self.assertRaises(PermissionError):d.advance('lint',False)
        with self.assertRaises(RuntimeError):d.advance('lint')
    def test_failed_backup(self):
        d=Delivery()
        for s in STAGES[:5]:d.advance(s)
        with self.assertRaises(PermissionError):d.advance('backup',False)
    def test_failed_slo(self):
        d=Delivery()
        for s in STAGES[:7]:d.advance(s)
        with self.assertRaises(PermissionError):d.advance('slo',False)
    def test_duplicate_stage(self):
        d=Delivery();d.advance('lint')
        with self.assertRaises(ValueError):d.advance('lint')
    def test_extra_stage(self):
        d=Delivery()
        for s in STAGES:d.advance(s)
        with self.assertRaises(ValueError):d.advance('destroy')
    def test_missing_audit(self):
        d=Delivery()
        for s in STAGES[:-1]:d.advance(s)
        self.assertNotIn('audit',d.completed)
if __name__=='__main__':unittest.main()
