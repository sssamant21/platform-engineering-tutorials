import copy,json,unittest
from pathlib import Path
from allocate import allocate,distribute
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/safe.json').read_text())
POLICY=json.loads((ROOT/'policy.json').read_text())
class AllocationTests(unittest.TestCase):
    def test_safe(self):
        e,r=allocate(SAFE,POLICY);self.assertEqual(e,[]);self.assertEqual(r['source_cents'],2334)
    def test_shared(self):self.assertEqual(distribute(1001,{'payments':2,'analytics':1}),{'analytics':334,'payments':667})
    def test_rounding(self):self.assertEqual(distribute(1,{'a':1,'b':1}),{'a':1,'b':0})
    def test_zero(self):self.assertEqual(distribute(0,{'a':1}),{'a':0})
    def test_total(self):self.assertEqual(sum(distribute(1001,{'a':1,'b':1,'c':1}).values()),1001)
    def test_invalid_cents(self):
        with self.assertRaises(ValueError):distribute(-1,{'a':1})
    def test_bool(self):
        with self.assertRaises(ValueError):distribute(True,{'a':1})
    def test_empty(self):
        with self.assertRaises(ValueError):distribute(10,{})
    def test_bad_weight(self):
        with self.assertRaises(ValueError):distribute(10,{'a':0})
    def test_bad_doc(self):self.assertTrue(allocate({},POLICY)[0])
    def test_unallocated(self):self.assertEqual(allocate(SAFE,POLICY)[1]['unallocated_cents'],99)
    def test_allocated(self):self.assertEqual(allocate(SAFE,POLICY)[1]['allocated_cents'],2235)
    def test_duplicate(self):
        d=copy.deepcopy(SAFE);d['records'].append(d['records'][0]);self.assertTrue(allocate(d,POLICY)[0])
    def test_no_shared_weight(self):
        d=copy.deepcopy(SAFE);d['records'][1]['weights']={};self.assertTrue(allocate(d,POLICY)[0])
if __name__=="__main__":unittest.main()
