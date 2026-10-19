import json,unittest
from pathlib import Path
from drift_assess import assess
SAFE=json.loads((Path(__file__).parent/'fixtures/drift.json').read_text())
class DriftTests(unittest.TestCase):
    def test_clean(self):self.assertEqual(assess({'a':1},{'a':1},{'a':1}),([],[]))
    def test_fixture(self):self.assertEqual(len(assess(**SAFE)[1]),2)
    def test_unmanaged(self):self.assertEqual(assess({}, {}, {'a':1})[1][0]['kind'],'unmanaged')
    def test_missing_remote(self):self.assertEqual(assess({'a':1},{'a':1},{})[1][0]['kind'],'missing_remote')
    def test_state_only(self):self.assertEqual(assess({}, {'a':1},{})[1][0]['kind'],'state_only')
    def test_desired_only(self):self.assertEqual(assess({'a':1},{},{})[1][0]['kind'],'desired_only')
    def test_mismatch(self):self.assertEqual(assess({'a':1},{'a':1},{'a':2})[1][0]['kind'],'mismatch')
    def test_incomplete(self):self.assertTrue(assess({}, {}, {},False)[0])
    def test_invalid(self):self.assertTrue(assess(None,{}, {})[0])
    def test_missing_managed(self):self.assertEqual(assess({'a':1},{},{'a':1})[1][0]['kind'],'mismatch')
if __name__=="__main__":unittest.main()
