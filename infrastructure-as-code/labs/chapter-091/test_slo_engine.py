import unittest
from slo_engine import assess
class SloTests(unittest.TestCase):
    def test_success(self):
        errors,result=assess(10000,5);self.assertEqual(errors,[]);self.assertAlmostEqual(result['availability'],0.9995)
    def test_budget(self):
        errors,result=assess(10000,20);self.assertEqual(errors,[]);self.assertGreater(result['budget_consumed'],1)
    def test_burn(self):
        errors,result=assess(10000,5,window_total=1000,window_errors=2);self.assertEqual(errors,[]);self.assertAlmostEqual(result['burn_rate'],2)
    def test_zero(self):self.assertTrue(assess(0,0)[0])
    def test_negative(self):self.assertTrue(assess(10,-1)[0])
    def test_more_errors(self):self.assertTrue(assess(10,11)[0])
    def test_bool_total(self):self.assertTrue(assess(True,0)[0])
    def test_bool_errors(self):self.assertTrue(assess(10,False)[0])
    def test_objective_zero(self):self.assertTrue(assess(10,0,objective=0)[0])
    def test_objective_one(self):self.assertTrue(assess(10,0,objective=1)[0])
    def test_nan(self):self.assertTrue(assess(10,0,objective=float('nan'))[0])
    def test_bad_window(self):self.assertTrue(assess(10,0,window_total=0,window_errors=0)[0])
    def test_window_errors(self):self.assertTrue(assess(10,0,window_total=10,window_errors=11)[0])
    def test_no_errors(self):self.assertEqual(assess(100,0)[1]['budget_consumed'],0)
if __name__=="__main__":unittest.main()
