import copy,json,unittest
from pathlib import Path
from coverage_gate import assess
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/coverage-safe.json').read_text())
class CoverageTests(unittest.TestCase):
    def bad(self,**changes):self.assertTrue(assess(dict(SAFE,**changes)))
    def test_safe(self):self.assertEqual(assess(SAFE),[])
    def test_invalid(self):self.assertTrue(assess(None))
    def test_layers(self):self.bad(layers=['static'])
    def test_duplicate_layer(self):self.bad(layers=SAFE['layers']+['static'])
    def test_no_ids(self):self.bad(test_ids=[])
    def test_duplicate_ids(self):self.bad(test_ids=['T-1']*12)
    def test_bad_id(self):self.bad(test_ids=['']*12)
    def test_skipped(self):self.bad(skipped_critical=1)
    def test_negative(self):self.bad(negative_policy_tests=False)
    def test_restore(self):self.bad(db_restore_claimed=False)
    def test_boolean_skipped(self):self.bad(skipped_critical=True)
if __name__=="__main__":unittest.main()
