import unittest
from savings import estimate
class SavingsTests(unittest.TestCase):
    def test_valid(self):self.assertEqual(estimate('1000','750')['projected_savings_usd'],'250.00')
    def test_percent(self):self.assertEqual(estimate('1000','750')['projected_savings_pct'],'25.00')
    def test_equal(self):self.assertEqual(estimate(100,100)['projected_savings_usd'],'0.00')
    def test_negative_savings(self):self.assertEqual(estimate(100,150)['projected_savings_usd'],'-50.00')
    def test_zero_baseline(self):self.assertIsNone(estimate(0,10))
    def test_negative_baseline(self):self.assertIsNone(estimate(-1,10))
    def test_negative_target(self):self.assertIsNone(estimate(100,-1))
    def test_nan(self):self.assertIsNone(estimate('NaN',10))
    def test_inf(self):self.assertIsNone(estimate('Infinity',10))
    def test_bool(self):self.assertIsNone(estimate(True,10))
    def test_decimal(self):self.assertEqual(estimate('10.50','10.25')['projected_savings_usd'],'0.25')
if __name__=="__main__":unittest.main()
