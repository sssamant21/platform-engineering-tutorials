import unittest
from pipeline import Promotion,STAGES
class PipelineTests(unittest.TestCase):
    def test_happy_path(self):
        p=Promotion()
        for stage in STAGES:p.advance(stage)
        self.assertEqual(tuple(p.completed),STAGES)
    def test_skip_preview(self):
        p=Promotion();p.advance('source')
        with self.assertRaises(ValueError):p.advance('preview')
    def test_fail_source(self):
        with self.assertRaises(PermissionError):Promotion().advance('source',False)
    def test_fail_policy(self):
        p=Promotion()
        for stage in STAGES[:3]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('policy',False)
    def test_fail_approval(self):
        p=Promotion()
        for stage in STAGES[:4]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('approve',False)
    def test_fail_backup(self):
        p=Promotion()
        for stage in STAGES[:5]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('backup',False)
    def test_fail_revalidation(self):
        p=Promotion()
        for stage in STAGES[:6]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('revalidate',False)
    def test_fail_canary(self):
        p=Promotion()
        for stage in STAGES[:7]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('canary',False)
    def test_fail_health(self):
        p=Promotion()
        for stage in STAGES[:8]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('health',False)
    def test_fail_audit(self):
        p=Promotion()
        for stage in STAGES[:10]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('audit',False)
    def test_stopped(self):
        p=Promotion()
        with self.assertRaises(PermissionError):p.advance('source',False)
        with self.assertRaises(RuntimeError):p.advance('source')
    def test_duplicate(self):
        p=Promotion();p.advance('source')
        with self.assertRaises(ValueError):p.advance('source')
    def test_extra(self):
        p=Promotion()
        for stage in STAGES:p.advance(stage)
        with self.assertRaises(ValueError):p.advance('destroy')
if __name__=="__main__":unittest.main()
