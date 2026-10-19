import unittest
from lifecycle import Lease,STAGES
class LeaseTests(unittest.TestCase):
    def test_success(self):
        l=Lease()
        for s in STAGES:l.advance(s,owned_resources=0)
        self.assertEqual(tuple(l.stages),STAGES)
    def test_skip(self):
        with self.assertRaises(ValueError):Lease().advance('provisioned')
    def test_duplicate(self):
        l=Lease();l.advance('requested')
        with self.assertRaises(ValueError):l.advance('requested')
    def test_halted(self):
        l=Lease()
        with self.assertRaises(PermissionError):l.advance('requested',False)
        with self.assertRaises(RuntimeError):l.advance('requested')
    def test_no_cleanup_proof(self):
        l=Lease()
        for s in STAGES[:6]:l.advance(s)
        with self.assertRaises(PermissionError):l.advance('verified')
    def test_extra(self):
        l=Lease()
        for s in STAGES:l.advance(s,owned_resources=0)
        with self.assertRaises(ValueError):l.advance('delete')
    def test_failed_requested(self):
        l=Lease()
        for stage in STAGES[:0]:l.advance(stage)
        with self.assertRaises(PermissionError):l.advance('requested',False)
    def test_failed_leased(self):
        l=Lease()
        for stage in STAGES[:1]:l.advance(stage)
        with self.assertRaises(PermissionError):l.advance('leased',False)
    def test_failed_provisioned(self):
        l=Lease()
        for stage in STAGES[:2]:l.advance(stage)
        with self.assertRaises(PermissionError):l.advance('provisioned',False)
    def test_failed_tested(self):
        l=Lease()
        for stage in STAGES[:3]:l.advance(stage)
        with self.assertRaises(PermissionError):l.advance('tested',False)
    def test_failed_cleanup_pending(self):
        l=Lease()
        for stage in STAGES[:4]:l.advance(stage)
        with self.assertRaises(PermissionError):l.advance('cleanup_pending',False)
    def test_failed_destroyed(self):
        l=Lease()
        for stage in STAGES[:5]:l.advance(stage)
        with self.assertRaises(PermissionError):l.advance('destroyed',False)
    def test_failed_verified(self):
        l=Lease()
        for stage in STAGES[:6]:l.advance(stage)
        with self.assertRaises(PermissionError):l.advance('verified',False)
    def test_failed_closed(self):
        l=Lease()
        for stage in STAGES[:7]:l.advance(stage)
        with self.assertRaises(PermissionError):l.advance('closed',False)
if __name__=="__main__":unittest.main()
