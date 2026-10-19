import unittest
from promotion import Promotion,STAGES
class PromotionTests(unittest.TestCase):
    def test_success(self):
        p=Promotion()
        for s in STAGES:p.advance(s)
        self.assertEqual(tuple(p.completed),STAGES)
    def test_skip(self):
        with self.assertRaises(ValueError):Promotion().advance('approval')
    def test_duplicate(self):
        p=Promotion();p.advance('source')
        with self.assertRaises(ValueError):p.advance('source')
    def test_halted(self):
        p=Promotion()
        with self.assertRaises(PermissionError):p.advance('source',False)
        with self.assertRaises(RuntimeError):p.advance('source')
    def test_extra(self):
        p=Promotion()
        for s in STAGES:p.advance(s)
        with self.assertRaises(ValueError):p.advance('destroy')
    def test_failed_source(self):
        p=Promotion()
        for stage in STAGES[:0]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('source',False)
    def test_failed_preview(self):
        p=Promotion()
        for stage in STAGES[:1]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('preview',False)
    def test_failed_scan(self):
        p=Promotion()
        for stage in STAGES[:2]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('scan',False)
    def test_failed_policy(self):
        p=Promotion()
        for stage in STAGES[:3]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('policy',False)
    def test_failed_approval(self):
        p=Promotion()
        for stage in STAGES[:4]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('approval',False)
    def test_failed_backup(self):
        p=Promotion()
        for stage in STAGES[:5]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('backup',False)
    def test_failed_canary(self):
        p=Promotion()
        for stage in STAGES[:6]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('canary',False)
    def test_failed_health(self):
        p=Promotion()
        for stage in STAGES[:7]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('health',False)
    def test_failed_promote(self):
        p=Promotion()
        for stage in STAGES[:8]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('promote',False)
    def test_failed_audit(self):
        p=Promotion()
        for stage in STAGES[:9]:p.advance(stage)
        with self.assertRaises(PermissionError):p.advance('audit',False)
if __name__=="__main__":unittest.main()
