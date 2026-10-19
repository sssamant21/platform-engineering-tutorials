import unittest
from reconcile import reconcile
class ReconcileTests(unittest.TestCase):
    def test_valid(self):self.assertEqual(reconcile({'source_cents':10,'ledger_cents':{'a':8,'__unallocated__':2},'allocated_cents':8,'unallocated_cents':2}),[])
    def test_invalid(self):self.assertTrue(reconcile(None))
    def test_empty(self):self.assertTrue(reconcile({}))
    def test_bool(self):self.assertTrue(reconcile({'source_cents':True,'ledger_cents':{'a':1},'allocated_cents':1,'unallocated_cents':0}))
    def test_negative(self):self.assertTrue(reconcile({'source_cents':-1,'ledger_cents':{'a':1},'allocated_cents':1,'unallocated_cents':0}))
    def test_residual(self):self.assertTrue(reconcile({'source_cents':11,'ledger_cents':{'a':10},'allocated_cents':10,'unallocated_cents':0}))
    def test_subtotal(self):self.assertTrue(reconcile({'source_cents':10,'ledger_cents':{'a':10},'allocated_cents':9,'unallocated_cents':0}))
    def test_ledger_negative(self):self.assertTrue(reconcile({'source_cents':10,'ledger_cents':{'a':-1},'allocated_cents':-1,'unallocated_cents':0}))
    def test_no_ledger(self):self.assertTrue(reconcile({'source_cents':0,'ledger_cents':{},'allocated_cents':0,'unallocated_cents':0}))
    def test_unallocated_only(self):self.assertEqual(reconcile({'source_cents':4,'ledger_cents':{'__unallocated__':4},'allocated_cents':0,'unallocated_cents':4}),[])
if __name__=="__main__":unittest.main()
