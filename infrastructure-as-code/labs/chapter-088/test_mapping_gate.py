import json,unittest
from pathlib import Path
from mapping_gate import assess
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/catalog-safe.json').read_text())
class MappingTests(unittest.TestCase):
    def bad(self,**changes):
        rows=[dict(r) for r in SAFE];rows[0].update(changes);self.assertTrue(assess(rows))
    def test_safe(self):self.assertEqual(assess(SAFE),[])
    def test_invalid(self):self.assertTrue(assess(None))
    def test_missing(self):self.assertTrue(assess(SAFE[:7]))
    def test_duplicate(self):self.bad(id='IAC-002')
    def test_owner(self):self.bad(owner='')
    def test_objective(self):self.bad(objective='')
    def test_framework(self):self.bad(framework='')
    def test_implementation(self):self.bad(implementation='')
    def test_evidence(self):self.bad(evidence='')
    def test_frequency(self):self.bad(frequency='')
    def test_invalid_row(self):self.assertTrue(assess([None]))
if __name__=="__main__":unittest.main()
