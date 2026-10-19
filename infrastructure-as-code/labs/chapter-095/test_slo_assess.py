import unittest
from slo_assess import assess
class SloTests(unittest.TestCase):
    def test_valid(self):
        e,r=assess(10000,5);self.assertEqual(e,[]);self.assertAlmostEqual(r['availability'],0.9995)
    def test_exhausted(self):self.assertGreater(assess(10000,20)[1]['budget_consumed'],1)
    def test_burn(self):self.assertAlmostEqual(assess(10000,5,windows={'5m':[1000,2]})[1]['burn_rates']['5m'],2)
    def test_zero(self):self.assertTrue(assess(0,0)[0])
    def test_negative(self):self.assertTrue(assess(10,-1)[0])
    def test_excess(self):self.assertTrue(assess(10,11)[0])
    def test_bool_total(self):self.assertTrue(assess(True,0)[0])
    def test_bool_bad(self):self.assertTrue(assess(10,False)[0])
    def test_objective_zero(self):self.assertTrue(assess(10,0,0)[0])
    def test_objective_one(self):self.assertTrue(assess(10,0,1)[0])
    def test_nan(self):self.assertTrue(assess(10,0,float('nan'))[0])
    def test_empty_windows(self):self.assertTrue(assess(10,0,windows={})[0])
    def test_invalid_window(self):self.assertTrue(assess(10,0,windows={'5m':None})[0])
    def test_bad_window_counts(self):self.assertTrue(assess(10,0,windows={'5m':[10,11]})[0])
if __name__=="__main__":unittest.main()
