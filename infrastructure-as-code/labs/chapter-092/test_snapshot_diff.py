import json,unittest
from pathlib import Path
from snapshot_diff import assess
SAFE=json.loads((Path(__file__).parent/'fixtures/snapshots.json').read_text())
class SnapshotTests(unittest.TestCase):
    def test_clean(self):self.assertEqual(assess({'a':1},{'a':1},{'a':1}),([],[]))
    def test_fixture(self):
        errors,findings=assess(**SAFE);self.assertEqual(errors,[]);self.assertEqual(len(findings),2)
    def test_unmanaged(self):self.assertEqual(assess({}, {}, {'a':1})[1][0]['kind'],'unmanaged')
    def test_state_only(self):self.assertEqual(assess({}, {'a':1}, {})[1][0]['kind'],'state_only')
    def test_desired_only(self):self.assertEqual(assess({'a':1}, {}, {})[1][0]['kind'],'desired_only')
    def test_missing_remote(self):self.assertEqual(assess({'a':1},{'a':1},{})[1][0]['kind'],'missing_remote')
    def test_unowned_state(self):self.assertEqual(assess({}, {'a':1},{'a':1})[1][0]['kind'],'unowned_state')
    def test_unmanaged_desired(self):self.assertEqual(assess({'a':1},{},{'a':1})[1][0]['kind'],'unmanaged_desired')
    def test_mismatch(self):self.assertEqual(assess({'a':1},{'a':1},{'a':2})[1][0]['kind'],'three_way_mismatch')
    def test_invalid(self):self.assertTrue(assess(None,{}, {})[0])
    def test_empty_key(self):self.assertTrue(assess({'':1},{},{})[0])
    def test_bad_value(self):self.assertTrue(assess({'a':object()},{},{})[0])
if __name__=="__main__":unittest.main()
