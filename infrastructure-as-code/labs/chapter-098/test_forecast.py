import json,unittest
from pathlib import Path
from forecast import project
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/safe.json').read_text())
POLICY=json.loads((ROOT/'policy.json').read_text())
class ForecastTests(unittest.TestCase):
    def test_valid(self):self.assertEqual(project(SAFE,POLICY,10)[0],[])
    def test_mean(self):self.assertEqual(project(SAFE,POLICY,10)[1]['daily_average_usd'],'130.00')
    def test_forecast(self):self.assertEqual(project(SAFE,POLICY,10)[1]['remaining_forecast_usd'],'1300.00')
    def test_observed(self):self.assertEqual(project(SAFE,POLICY,10)[1]['observed_usd'],'910.00')
    def test_zero(self):self.assertEqual(project(SAFE,POLICY,0)[1]['remaining_forecast_usd'],'0.00')
    def test_negative(self):self.assertTrue(project(SAFE,POLICY,-1)[0])
    def test_too_far(self):self.assertTrue(project(SAFE,POLICY,32)[0])
    def test_bool(self):self.assertTrue(project(SAFE,POLICY,True)[0])
    def test_bad_doc(self):self.assertTrue(project({},POLICY,5)[0])
    def test_bad_policy(self):self.assertTrue(project(SAFE,{},5)[0])
if __name__=="__main__":unittest.main()
