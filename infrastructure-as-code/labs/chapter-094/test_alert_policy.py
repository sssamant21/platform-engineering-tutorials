import json,unittest
from pathlib import Path
from alert_policy import classify
SAFE=json.loads((Path(__file__).parent/'fixtures/burn-safe.json').read_text())
class AlertTests(unittest.TestCase):
    def test_ok(self):self.assertEqual(classify(**SAFE),'OK')
    def test_page_fast(self):
        b=dict(SAFE['burns'],**{'5m':15,'1h':15});self.assertEqual(classify(b,SAFE['counts']),'PAGE')
    def test_page_slow(self):
        b=dict(SAFE['burns'],**{'30m':7,'6h':7});self.assertEqual(classify(b,SAFE['counts']),'PAGE')
    def test_ticket(self):
        b=dict(SAFE['burns'],**{'6h':2});self.assertEqual(classify(b,SAFE['counts']),'TICKET')
    def test_stale(self):self.assertEqual(classify(SAFE['burns'],SAFE['counts'],False),'UNKNOWN')
    def test_missing(self):self.assertEqual(classify({},SAFE['counts']),'UNKNOWN')
    def test_missing_counts(self):self.assertEqual(classify(SAFE['burns'],{}),'UNKNOWN')
    def test_invalid_burn(self):
        b=dict(SAFE['burns'],**{'5m':-1});self.assertEqual(classify(b,SAFE['counts']),'UNKNOWN')
    def test_invalid_count(self):
        c=dict(SAFE['counts'],**{'5m':0});self.assertEqual(classify(SAFE['burns'],c),'UNKNOWN')
    def test_bool_count(self):
        c=dict(SAFE['counts'],**{'5m':True});self.assertEqual(classify(SAFE['burns'],c),'UNKNOWN')
    def test_min_invalid(self):self.assertEqual(classify(SAFE['burns'],SAFE['counts'],min_requests=0),'UNKNOWN')
    def test_low_sample(self):self.assertEqual(classify(SAFE['burns'],SAFE['counts'],min_requests=100000),'UNKNOWN')
    def test_one_window_not_page(self):
        b=dict(SAFE['burns'],**{'5m':15,'1h':1});self.assertNotEqual(classify(b,SAFE['counts']),'PAGE')
if __name__=="__main__":unittest.main()
