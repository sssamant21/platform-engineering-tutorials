import json,unittest
from pathlib import Path
from remediation_assess import decide
SAFE=json.loads((Path(__file__).parent/'fixtures/change-safe.json').read_text())
class RemediationTests(unittest.TestCase):
    def result(self,expected,**changes):self.assertEqual(decide(dict(SAFE,**changes)),expected)
    def test_safe(self):self.result('PROPOSAL_ONLY')
    def test_prod(self):self.result('HOLD',environment='production')
    def test_medium(self):self.result('HOLD',risk='medium')
    def test_destructive(self):self.result('QUARANTINE',destructive=True)
    def test_database(self):self.result('QUARANTINE',database=True)
    def test_high(self):self.result('QUARANTINE',risk='high')
    def test_critical(self):self.result('QUARANTINE',risk='critical')
    def test_stale(self):self.result('QUARANTINE',telemetry_fresh=False)
    def test_partial(self):self.result('QUARANTINE',inventory_complete=False)
    def test_no_state(self):self.result('QUARANTINE',state_preserved=False)
    def test_unapproved(self):self.result('HOLD',approved=False)
    def test_slo(self):self.result('HOLD',slo_healthy=False)
    def test_incident(self):self.result('HOLD',active_incident=True)
    def test_invalid(self):self.assertEqual(decide(None),'QUARANTINE')
    def test_missing(self):self.assertEqual(decide({}),'QUARANTINE')
    def test_wrong_type(self):self.result('QUARANTINE',destructive='false')
if __name__=="__main__":unittest.main()
