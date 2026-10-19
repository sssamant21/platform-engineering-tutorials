import json,unittest
from pathlib import Path
from dashboard_gate import assess
SAFE=json.loads((Path(__file__).parent/'fixtures/dashboard-safe.json').read_text())
class DashboardTests(unittest.TestCase):
    def bad(self,**changes):self.assertTrue(assess(dict(SAFE,**changes)))
    def test_valid(self):self.assertEqual(assess(SAFE),[])
    def test_invalid(self):self.assertTrue(assess(None))
    def test_panels(self):self.bad(panels=['pipeline'])
    def test_duplicate(self):self.bad(panels=SAFE['panels']+['pipeline'])
    def test_owner(self):self.bad(owner='')
    def test_runbook(self):self.bad(runbook='')
    def test_stale(self):self.bad(freshness_minutes=60)
    def test_negative(self):self.bad(freshness_minutes=-1)
    def test_boolean(self):self.bad(freshness_minutes=True)
    def test_missing_unknown(self):self.bad(unknown_when_missing=False)
if __name__=="__main__":unittest.main()
