import json,unittest
from pathlib import Path
from evidence_gate import assess
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/evidence-safe.json').read_text())
class EvidenceTests(unittest.TestCase):
    def bad(self,**changes):self.assertTrue(assess(dict(SAFE,**changes)))
    def test_safe(self):self.assertEqual(assess(SAFE),[])
    def test_invalid(self):self.assertTrue(assess(None))
    def test_missing_layer(self):self.bad(layers=['terraform'])
    def test_duplicate_layer(self):self.bad(layers=SAFE['layers']+['terraform'])
    def test_bad_layers(self):self.bad(layers=None)
    def test_assertions(self):self.bad(native_assertions=0)
    def test_negatives(self):self.bad(negative_tests=0)
    def test_skipped(self):self.bad(skipped_critical=1)
    def test_approval(self):self.bad(cleanup_signed_off=False)
    def test_bool_assertions(self):self.bad(native_assertions=True)
    def test_string_negatives(self):self.bad(negative_tests='10')
if __name__=="__main__":unittest.main()
