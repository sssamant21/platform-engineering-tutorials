import json,unittest
from pathlib import Path
from incident_assess import assess,candidates
DATA=json.loads((Path(__file__).parent/'fixtures/incident.json').read_text())
EVENTS=[{'event_id':'a','change_id':'CHG-A','timestamp':'2026-10-19T19:55:00Z'},{'event_id':'b','change_id':'CHG-A','timestamp':'2026-10-19T20:00:00Z'}]
class IncidentTests(unittest.TestCase):
    def test_valid(self):self.assertEqual(assess(EVENTS),[])
    def test_empty(self):self.assertTrue(assess([]))
    def test_bad(self):self.assertTrue(assess(None))
    def test_duplicate(self):self.assertTrue(assess(EVENTS+[EVENTS[0]]))
    def test_reverse(self):self.assertTrue(assess(list(reversed(EVENTS))))
    def test_naive(self):self.assertTrue(assess([dict(EVENTS[0],timestamp='2026-10-19T19:55:00')]))
    def test_non_utc(self):self.assertTrue(assess([dict(EVENTS[0],timestamp='2026-10-19T19:55:00+02:00')]))
    def test_missing_id(self):self.assertTrue(assess([dict(EVENTS[0],event_id='')]))
    def test_missing_change(self):self.assertTrue(assess([dict(EVENTS[0],change_id='')]))
    def test_rank(self):self.assertEqual(candidates(**DATA)[1][0]['change_id'],'CHG-095-A')
    def test_not_causal(self):self.assertFalse(candidates(**DATA)[1][0]['causal_proof'])
    def test_invalid_window(self):self.assertTrue(candidates(**DATA,window=0)[0])
    def test_bad_onset(self):self.assertTrue(candidates(dict(DATA['incident'],onset='bad'),DATA['changes'])[0])
    def test_future(self):self.assertEqual(candidates(DATA['incident'],[dict(DATA['changes'][0],timestamp='2026-10-19T21:00:00Z')])[1],[])
if __name__=="__main__":unittest.main()
