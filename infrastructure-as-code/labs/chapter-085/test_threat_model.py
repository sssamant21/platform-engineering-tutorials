import copy,json,unittest
from pathlib import Path
from threat_model import assess
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/threat-safe.json').read_text())
class ThreatTests(unittest.TestCase):
    def bad(self,**changes):self.assertTrue(assess([dict(SAFE[0],**changes)]))
    def test_safe(self):self.assertEqual(assess(SAFE),[])
    def test_invalid(self):self.assertTrue(assess(None))
    def test_invalid_item(self):self.assertTrue(assess([None]))
    def test_category(self):self.bad(category='unknown')
    def test_owner(self):self.bad(owner='')
    def test_asset(self):self.bad(asset='')
    def test_mitigation(self):self.bad(mitigation='')
    def test_likelihood(self):self.bad(likelihood=0)
    def test_impact(self):self.bad(impact=6)
    def test_open_high(self):self.bad(status='open')
    def test_invalid_status(self):self.bad(status='ignored')
    def test_open_low(self):self.assertEqual(assess([dict(SAFE[0],likelihood=1,impact=1,status='open')]),[])
if __name__=="__main__":unittest.main()
