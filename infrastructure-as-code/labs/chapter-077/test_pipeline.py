import unittest
from pipeline import Pipeline,STAGES
class PipelineTests(unittest.TestCase):
    def test_success(self):
        p=Pipeline()
        for s in STAGES:p.advance(s)
        self.assertEqual(tuple(p.completed),STAGES)
    def test_skip_plan(self):
        p=Pipeline();p.advance('validate')
        with self.assertRaises(ValueError):p.advance('plan')
    def test_fail_init(self):
        p=Pipeline();p.advance('validate')
        with self.assertRaises(PermissionError):p.advance('init',False)
    def test_fail_policy(self):
        p=Pipeline()
        for s in STAGES[:3]:p.advance(s)
        with self.assertRaises(PermissionError):p.advance('policy',False)
    def test_fail_approval(self):
        p=Pipeline()
        for s in STAGES[:4]:p.advance(s)
        with self.assertRaises(PermissionError):p.advance('approval',False)
    def test_fail_backup(self):
        p=Pipeline()
        for s in STAGES[:5]:p.advance(s)
        with self.assertRaises(PermissionError):p.advance('backup',False)
    def test_fail_revalidate(self):
        p=Pipeline()
        for s in STAGES[:6]:p.advance(s)
        with self.assertRaises(PermissionError):p.advance('revalidate',False)
    def test_fail_health(self):
        p=Pipeline()
        for s in STAGES[:8]:p.advance(s)
        with self.assertRaises(PermissionError):p.advance('health',False)
    def test_fail_audit(self):
        p=Pipeline()
        for s in STAGES[:9]:p.advance(s)
        with self.assertRaises(PermissionError):p.advance('audit',False)
    def test_halted(self):
        p=Pipeline()
        with self.assertRaises(PermissionError):p.advance('validate',False)
        with self.assertRaises(RuntimeError):p.advance('validate')
    def test_duplicate(self):
        p=Pipeline();p.advance('validate')
        with self.assertRaises(ValueError):p.advance('validate')
    def test_extra(self):
        p=Pipeline()
        for s in STAGES:p.advance(s)
        with self.assertRaises(ValueError):p.advance('destroy')
if __name__=="__main__":unittest.main()
