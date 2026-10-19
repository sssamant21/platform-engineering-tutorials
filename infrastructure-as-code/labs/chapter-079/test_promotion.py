import unittest
from promotion import Promotion,STAGES
class PromotionTests(unittest.TestCase):
    def test_success(self):
        p=Promotion()
        for s in STAGES:p.advance(s)
        self.assertEqual(tuple(p.completed),STAGES)
    def test_skip_inventory(self):
        p=Promotion();p.advance('validate')
        with self.assertRaises(ValueError):p.advance('dryrun')
    def test_failed_validate(self):
        with self.assertRaises(PermissionError):Promotion().advance('validate',False)
    def test_failed_dryrun(self):
        p=Promotion()
        for s in STAGES[:2]:p.advance(s)
        with self.assertRaises(PermissionError):p.advance('dryrun',False)
    def test_failed_diff(self):
        p=Promotion()
        for s in STAGES[:3]:p.advance(s)
        with self.assertRaises(PermissionError):p.advance('diff',False)
    def test_failed_policy(self):
        p=Promotion()
        for s in STAGES[:4]:p.advance(s)
        with self.assertRaises(PermissionError):p.advance('policy',False)
    def test_failed_approval(self):
        p=Promotion()
        for s in STAGES[:5]:p.advance(s)
        with self.assertRaises(PermissionError):p.advance('approve',False)
    def test_failed_backup(self):
        p=Promotion()
        for s in STAGES[:6]:p.advance(s)
        with self.assertRaises(PermissionError):p.advance('backup',False)
    def test_failed_canary(self):
        p=Promotion()
        for s in STAGES[:7]:p.advance(s)
        with self.assertRaises(PermissionError):p.advance('canary',False)
    def test_failed_health(self):
        p=Promotion()
        for s in STAGES[:8]:p.advance(s)
        with self.assertRaises(PermissionError):p.advance('health',False)
    def test_failed_audit(self):
        p=Promotion()
        for s in STAGES[:10]:p.advance(s)
        with self.assertRaises(PermissionError):p.advance('audit',False)
    def test_halted(self):
        p=Promotion()
        with self.assertRaises(PermissionError):p.advance('validate',False)
        with self.assertRaises(RuntimeError):p.advance('validate')
    def test_duplicate(self):
        p=Promotion();p.advance('validate')
        with self.assertRaises(ValueError):p.advance('validate')
    def test_extra(self):
        p=Promotion()
        for s in STAGES:p.advance(s)
        with self.assertRaises(ValueError):p.advance('destroy')
if __name__=="__main__":unittest.main()
