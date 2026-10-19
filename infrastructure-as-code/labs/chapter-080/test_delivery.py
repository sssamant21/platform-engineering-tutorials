import unittest
from delivery import Delivery,STAGES
class DeliveryTests(unittest.TestCase):
    def test_success(self):
        d=Delivery()
        for s in STAGES:d.advance(s)
        self.assertEqual(tuple(d.completed),STAGES)
    def test_skip(self):
        with self.assertRaises(ValueError):Delivery().advance('preview')
    def test_failed_source(self):
        with self.assertRaises(PermissionError):Delivery().advance('source',False)
    def test_halted(self):
        d=Delivery()
        with self.assertRaises(PermissionError):d.advance('source',False)
        with self.assertRaises(RuntimeError):d.advance('source')
    def test_duplicate(self):
        d=Delivery();d.advance('source')
        with self.assertRaises(ValueError):d.advance('source')
    def test_extra(self):
        d=Delivery()
        for s in STAGES:d.advance(s)
        with self.assertRaises(ValueError):d.advance('destroy')
    def test_failed_scan(self):
        d=Delivery()
        for step in STAGES[:1]:d.advance(step)
        with self.assertRaises(PermissionError):d.advance('scan',False)
    def test_failed_preview(self):
        d=Delivery()
        for step in STAGES[:2]:d.advance(step)
        with self.assertRaises(PermissionError):d.advance('preview',False)
    def test_failed_policy(self):
        d=Delivery()
        for step in STAGES[:3]:d.advance(step)
        with self.assertRaises(PermissionError):d.advance('policy',False)
    def test_failed_approval(self):
        d=Delivery()
        for step in STAGES[:4]:d.advance(step)
        with self.assertRaises(PermissionError):d.advance('approval',False)
    def test_failed_backup(self):
        d=Delivery()
        for step in STAGES[:5]:d.advance(step)
        with self.assertRaises(PermissionError):d.advance('backup',False)
    def test_failed_canary(self):
        d=Delivery()
        for step in STAGES[:6]:d.advance(step)
        with self.assertRaises(PermissionError):d.advance('canary',False)
    def test_failed_health(self):
        d=Delivery()
        for step in STAGES[:7]:d.advance(step)
        with self.assertRaises(PermissionError):d.advance('health',False)
    def test_failed_promote(self):
        d=Delivery()
        for step in STAGES[:8]:d.advance(step)
        with self.assertRaises(PermissionError):d.advance('promote',False)
    def test_failed_audit(self):
        d=Delivery()
        for step in STAGES[:9]:d.advance(step)
        with self.assertRaises(PermissionError):d.advance('audit',False)
if __name__=="__main__":unittest.main()
