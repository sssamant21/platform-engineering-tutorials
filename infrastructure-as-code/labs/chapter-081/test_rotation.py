import unittest
from rotation import Rotation,STAGES
class RotationTests(unittest.TestCase):
    def test_success(self):
        r=Rotation()
        for s in STAGES:r.advance(s)
        self.assertEqual(tuple(r.completed),STAGES)
    def test_skip(self):
        with self.assertRaises(ValueError):Rotation().advance('revoke')
    def test_duplicate(self):
        r=Rotation();r.advance('prepare')
        with self.assertRaises(ValueError):r.advance('prepare')
    def test_halted(self):
        r=Rotation()
        with self.assertRaises(PermissionError):r.advance('prepare',False)
        with self.assertRaises(RuntimeError):r.advance('prepare')
    def test_extra(self):
        r=Rotation()
        for s in STAGES:r.advance(s)
        with self.assertRaises(ValueError):r.advance('destroy')
    def test_fail_prepare(self):
        r=Rotation()
        for step in STAGES[:0]:r.advance(step)
        with self.assertRaises(PermissionError):r.advance('prepare',False)
    def test_fail_distribute(self):
        r=Rotation()
        for step in STAGES[:1]:r.advance(step)
        with self.assertRaises(PermissionError):r.advance('distribute',False)
    def test_fail_verify(self):
        r=Rotation()
        for step in STAGES[:2]:r.advance(step)
        with self.assertRaises(PermissionError):r.advance('verify',False)
    def test_fail_revoke(self):
        r=Rotation()
        for step in STAGES[:3]:r.advance(step)
        with self.assertRaises(PermissionError):r.advance('revoke',False)
    def test_fail_audit(self):
        r=Rotation()
        for step in STAGES[:4]:r.advance(step)
        with self.assertRaises(PermissionError):r.advance('audit',False)
if __name__=="__main__":unittest.main()
