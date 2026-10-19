import json,unittest
from pathlib import Path
from threat_model import assess
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/threats-safe.json').read_text())
UNSAFE=json.loads((ROOT/'fixtures/threats-unsafe.json').read_text())
class ThreatTests(unittest.TestCase):
    def test_safe(self):self.assertEqual(assess(SAFE),[])
    def test_unsafe(self):self.assertTrue(assess(UNSAFE))
    def test_invalid(self):self.assertTrue(assess('not a list'))
    def test_invalid_item(self):self.assertTrue(assess([None]))
    def test_invalid_category(self):self.assertTrue(assess([dict(SAFE[0],category='unknown')]))
    def test_missing_owner(self):self.assertTrue(assess([dict(SAFE[0],owner='')]))
    def test_missing_mitigation(self):self.assertTrue(assess([dict(SAFE[0],mitigation='')]))
    def test_unmitigated_high_risk(self):self.assertTrue(assess([dict(SAFE[0],status='open')]))
    def test_low_risk_open(self):self.assertEqual(assess([dict(SAFE[0],likelihood=1,impact=1,status='open')]),[])
    def test_bad_likelihood(self):self.assertTrue(assess([dict(SAFE[0],likelihood=0)]))
    def test_bad_impact(self):self.assertTrue(assess([dict(SAFE[0],impact=6)]))
if __name__=="__main__":unittest.main()
