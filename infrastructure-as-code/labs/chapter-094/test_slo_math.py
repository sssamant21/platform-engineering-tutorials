import unittest
from slo_math import calculate
class SloMathTests(unittest.TestCase):
    def test_success(self):
        e,r=calculate(10000,5);self.assertEqual(e,[]);self.assertAlmostEqual(r['availability'],0.9995)
    def test_budget(self):self.assertGreater(calculate(10000,20)[1]['budget_consumed'],1)
    def test_burn(self):
        e,r=calculate(10000,5,windows={'5m':[1000,2]});self.assertEqual(e,[]);self.assertAlmostEqual(r['burn_rates']['5m'],2)
    def test_zero(self):self.assertTrue(calculate(0,0)[0])
    def test_negative(self):self.assertTrue(calculate(10,-1)[0])
    def test_excess(self):self.assertTrue(calculate(10,11)[0])
    def test_bool_total(self):self.assertTrue(calculate(True,0)[0])
    def test_bool_bad(self):self.assertTrue(calculate(10,False)[0])
    def test_obj_zero(self):self.assertTrue(calculate(10,0,0)[0])
    def test_obj_one(self):self.assertTrue(calculate(10,0,1)[0])
    def test_obj_nan(self):self.assertTrue(calculate(10,0,float('nan'))[0])
    def test_windows_empty(self):self.assertTrue(calculate(10,0,windows={})[0])
    def test_windows_invalid(self):self.assertTrue(calculate(10,0,windows={'5m':None})[0])
    def test_windows_bad_counts(self):self.assertTrue(calculate(10,0,windows={'5m':[10,11]})[0])
    def test_no_errors(self):self.assertEqual(calculate(100,0)[1]['budget_consumed'],0)
if __name__=="__main__":unittest.main()
