import copy,json,unittest
from pathlib import Path
from allocate import allocate
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/safe.json').read_text())
POLICY=json.loads((ROOT/'policy.json').read_text())
class AllocationTests(unittest.TestCase):
    def test_valid(self):
        errors,result=allocate(SAFE,POLICY);self.assertEqual(errors,[]);self.assertEqual(result['total_usd'],'20.00')
    def test_platform(self):self.assertEqual(allocate(SAFE,POLICY)[1]['by_cost_center']['platform'],'15.90')
    def test_data(self):self.assertEqual(allocate(SAFE,POLICY)[1]['by_cost_center']['data'],'4.10')
    def test_unallocated(self):self.assertEqual(allocate(SAFE,POLICY)[1]['unallocated_usd'],'0.00')
    def test_bad(self):self.assertTrue(allocate([],POLICY)[0])
    def test_duplicate(self):
        e=copy.deepcopy(SAFE);e['records'].append(e['records'][0]);self.assertTrue(allocate(e,POLICY)[0])
    def test_bad_tag(self):
        e=copy.deepcopy(SAFE);e['records'][0]['tags']['cost_center']='';self.assertTrue(allocate(e,POLICY)[0])
    def test_currency(self):
        e=copy.deepcopy(SAFE);e['records'][0]['currency']='EUR';self.assertTrue(allocate(e,POLICY)[0])
    def test_cost(self):
        e=copy.deepcopy(SAFE);e['records'][0]['cost_usd']=-2;self.assertTrue(allocate(e,POLICY)[0])
    def test_zero(self):
        e=copy.deepcopy(SAFE);e['records'][0]['cost_usd']=0;self.assertEqual(allocate(e,POLICY)[0],[])
if __name__=="__main__":unittest.main()
