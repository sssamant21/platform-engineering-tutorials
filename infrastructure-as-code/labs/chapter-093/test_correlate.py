import json,unittest
from pathlib import Path
from correlate import rank
DATA=json.loads((Path(__file__).parent/'fixtures/correlation.json').read_text())
class CorrelationTests(unittest.TestCase):
    def test_rank(self):
        errors,out=rank(**DATA);self.assertEqual(errors,[]);self.assertEqual(out[0]['change_id'],'CHG-093-A')
    def test_no_causation(self):self.assertFalse(rank(**DATA)[1][0]['causal_proof'])
    def test_invalid_incident(self):self.assertTrue(rank(None,[])[0])
    def test_invalid_changes(self):self.assertTrue(rank(DATA['incident'],None)[0])
    def test_bad_window(self):self.assertTrue(rank(**DATA,window_minutes=0)[0])
    def test_bad_onset(self):self.assertTrue(rank(dict(DATA['incident'],onset='bad'),DATA['changes'])[0])
    def test_naive_onset(self):self.assertTrue(rank(dict(DATA['incident'],onset='2026-10-19T20:00:00'),DATA['changes'])[0])
    def test_wrong_service(self):
        _,out=rank(dict(DATA['incident'],service='other'),DATA['changes']);self.assertLess(out[0]['score'],9)
    def test_future_change(self):
        c=dict(DATA['changes'][0],timestamp='2026-10-19T21:00:00Z');self.assertEqual(rank(DATA['incident'],[c])[1],[])
    def test_invalid_change(self):self.assertTrue(rank(DATA['incident'],[None])[0])
    def test_missing_id(self):self.assertTrue(rank(DATA['incident'],[dict(DATA['changes'][0],change_id='')])[0])
    def test_bad_timestamp(self):self.assertTrue(rank(DATA['incident'],[dict(DATA['changes'][0],timestamp='bad')])[0])
if __name__=="__main__":unittest.main()
