import json,unittest
from pathlib import Path
from timeline import assess
SAFE=json.loads((Path(__file__).parent/'fixtures/timeline.json').read_text())
class TimelineTests(unittest.TestCase):
    def test_valid(self):self.assertEqual(assess(SAFE),[])
    def test_invalid(self):self.assertTrue(assess(None))
    def test_empty(self):self.assertTrue(assess([]))
    def test_entry(self):self.assertTrue(assess([None]))
    def test_duplicate(self):self.assertTrue(assess(SAFE+[SAFE[0]]))
    def test_missing_id(self):self.assertTrue(assess([dict(SAFE[0],event_id='')]))
    def test_missing_change(self):self.assertTrue(assess([dict(SAFE[0],change_id='')]))
    def test_order(self):self.assertTrue(assess(list(reversed(SAFE))))
    def test_bad_time(self):self.assertTrue(assess([dict(SAFE[0],timestamp='bad')]))
    def test_naive(self):self.assertTrue(assess([dict(SAFE[0],timestamp='2026-10-19T20:00:00')]))
    def test_non_utc(self):self.assertTrue(assess([dict(SAFE[0],timestamp='2026-10-19T20:00:00+02:00')]))
if __name__=="__main__":unittest.main()
