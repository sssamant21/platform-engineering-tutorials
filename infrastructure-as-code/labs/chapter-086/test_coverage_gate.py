import json,unittest
from pathlib import Path
from coverage_gate import assess
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/matrix-safe.json').read_text())
class CoverageTests(unittest.TestCase):
    def bad(self,**changes):self.assertTrue(assess(dict(SAFE,**changes)))
    def test_safe(self):self.assertEqual(assess(SAFE),[])
    def test_invalid(self):self.assertTrue(assess(None))
    def test_missing_layer(self):self.bad(layers=['format'])
    def test_duplicate_layer(self):self.bad(layers=SAFE['layers']+['unit'])
    def test_bad_layers(self):self.bad(layers=None)
    def test_low_negatives(self):self.bad(negative_cases=0)
    def test_skipped(self):self.bad(skipped_critical=1)
    def test_stale(self):self.bad(max_age_hours=25)
    def test_negative_age(self):self.bad(max_age_hours=-1)
    def test_bool_negatives(self):self.bad(negative_cases=True)
    def test_string_age(self):self.bad(max_age_hours='1')
if __name__=="__main__":unittest.main()
