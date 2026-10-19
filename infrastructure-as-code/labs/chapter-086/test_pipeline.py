import unittest
from pipeline import Pipeline,STAGES
class PipelineTests(unittest.TestCase):
    def test_success(self):
        p=Pipeline()
        for s in STAGES:p.advance(s)
        self.assertEqual(tuple(p.completed),STAGES)
    def test_skip(self):
        with self.assertRaises(ValueError):Pipeline().advance('approval')
    def test_duplicate(self):
        p=Pipeline();p.advance('source')
        with self.assertRaises(ValueError):p.advance('source')
    def test_halted(self):
        p=Pipeline()
        with self.assertRaises(PermissionError):p.advance('source',False)
        with self.assertRaises(RuntimeError):p.advance('source')
    def test_extra(self):
        p=Pipeline()
        for s in STAGES:p.advance(s)
        with self.assertRaises(ValueError):p.advance('destroy')
    def test_failed_source(self):
        p=Pipeline()
        for stage in STAGES[:0]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('source',False)
    def test_failed_format(self):
        p=Pipeline()
        for stage in STAGES[:1]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('format',False)
    def test_failed_static(self):
        p=Pipeline()
        for stage in STAGES[:2]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('static',False)
    def test_failed_unit(self):
        p=Pipeline()
        for stage in STAGES[:3]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('unit',False)
    def test_failed_policy(self):
        p=Pipeline()
        for stage in STAGES[:4]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('policy',False)
    def test_failed_plan(self):
        p=Pipeline()
        for stage in STAGES[:5]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('plan',False)
    def test_failed_integration(self):
        p=Pipeline()
        for stage in STAGES[:6]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('integration',False)
    def test_failed_restore(self):
        p=Pipeline()
        for stage in STAGES[:7]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('restore',False)
    def test_failed_canary(self):
        p=Pipeline()
        for stage in STAGES[:8]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('canary',False)
    def test_failed_evidence(self):
        p=Pipeline()
        for stage in STAGES[:9]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('evidence',False)
    def test_failed_approval(self):
        p=Pipeline()
        for stage in STAGES[:10]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('approval',False)
if __name__=="__main__":unittest.main()
