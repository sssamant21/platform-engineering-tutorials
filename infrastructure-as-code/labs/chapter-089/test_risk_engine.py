import json,unittest
from pathlib import Path
from risk_engine import assess
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/risk-safe.json').read_text())
class RiskTests(unittest.TestCase):
    def bad(self,**changes):self.assertTrue(assess(dict(SAFE,**changes))[0])
    def test_safe(self):self.assertEqual(assess(SAFE),([],20))
    def test_invalid(self):self.assertTrue(assess(None)[0])
    def test_missing(self):self.assertTrue(assess({})[0])
    def test_environment(self):self.bad(environment='unknown')
    def test_exposure(self):self.bad(exposure='unknown')
    def test_data(self):self.bad(data_impact='unknown')
    def test_destructive(self):self.bad(destructive='yes')
    def test_approved(self):self.bad(approved='yes')
    def test_critical(self):self.assertEqual(assess(dict(SAFE,environment='production',exposure='public',data_impact='regulated',destructive=True,approved=False)),([],100))
    def test_dev(self):self.assertEqual(assess(dict(SAFE,environment='dev',data_impact='none')),([],0))
    def test_unapproved(self):self.assertEqual(assess(dict(SAFE,approved=False)),([],40))
if __name__=="__main__":unittest.main()
