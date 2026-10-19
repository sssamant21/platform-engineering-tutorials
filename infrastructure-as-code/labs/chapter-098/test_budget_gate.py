import unittest
from budget_gate import classify
class BudgetTests(unittest.TestCase):
    def test_ok(self):self.assertEqual(classify(50,60,100),'OK')
    def test_watch(self):self.assertEqual(classify(50,80,100),'WATCH')
    def test_breach(self):self.assertEqual(classify(100,80,100),'BREACH')
    def test_forecast_breach(self):self.assertEqual(classify(10,120,100),'BREACH')
    def test_zero_budget(self):self.assertEqual(classify(1,2,0),'UNKNOWN')
    def test_negative(self):self.assertEqual(classify(-1,2,100),'UNKNOWN')
    def test_bool(self):self.assertEqual(classify(True,2,100),'UNKNOWN')
    def test_nan(self):self.assertEqual(classify('NaN',2,100),'UNKNOWN')
    def test_bad_threshold(self):self.assertEqual(classify(1,2,100,thresholds=[90]),'UNKNOWN')
    def test_decimal(self):self.assertEqual(classify('80.00','70.00','100.00'),'WATCH')
if __name__=="__main__":unittest.main()
