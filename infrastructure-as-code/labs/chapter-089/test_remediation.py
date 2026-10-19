import unittest
from remediation import Case,STAGES
class RemediationTests(unittest.TestCase):
    def test_success(self):
        c=Case()
        for s in STAGES:c.advance(s,independent_approval=True)
        self.assertEqual(tuple(c.stages),STAGES)
    def test_skip(self):
        with self.assertRaises(ValueError):Case().advance('closed')
    def test_duplicate(self):
        c=Case();c.advance('detected')
        with self.assertRaises(ValueError):c.advance('detected')
    def test_failed(self):
        c=Case()
        with self.assertRaises(PermissionError):c.advance('detected',False)
        with self.assertRaises(RuntimeError):c.advance('detected')
    def test_no_approval(self):
        c=Case();c.advance('detected');c.advance('classified')
        with self.assertRaises(PermissionError):c.advance('approved')
    def test_extra(self):
        c=Case()
        for s in STAGES:c.advance(s,independent_approval=True)
        with self.assertRaises(ValueError):c.advance('destroy')
    def test_failed_detected(self):
        c=Case()
        for stage in STAGES[:0]:c.advance(stage,independent_approval=True)
        with self.assertRaises(PermissionError):c.advance('detected',False,independent_approval=True)
    def test_failed_classified(self):
        c=Case()
        for stage in STAGES[:1]:c.advance(stage,independent_approval=True)
        with self.assertRaises(PermissionError):c.advance('classified',False,independent_approval=True)
    def test_failed_approved(self):
        c=Case()
        for stage in STAGES[:2]:c.advance(stage,independent_approval=True)
        with self.assertRaises(PermissionError):c.advance('approved',False,independent_approval=True)
    def test_failed_remediating(self):
        c=Case()
        for stage in STAGES[:3]:c.advance(stage,independent_approval=True)
        with self.assertRaises(PermissionError):c.advance('remediating',False,independent_approval=True)
    def test_failed_verified(self):
        c=Case()
        for stage in STAGES[:4]:c.advance(stage,independent_approval=True)
        with self.assertRaises(PermissionError):c.advance('verified',False,independent_approval=True)
    def test_failed_closed(self):
        c=Case()
        for stage in STAGES[:5]:c.advance(stage,independent_approval=True)
        with self.assertRaises(PermissionError):c.advance('closed',False,independent_approval=True)
if __name__=="__main__":unittest.main()
