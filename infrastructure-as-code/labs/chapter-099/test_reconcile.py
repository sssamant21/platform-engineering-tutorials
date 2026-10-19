import unittest
from reconcile import classify
class ReconcileTests(unittest.TestCase):
    def test_match(self):self.assertEqual(classify(100,100),'RECONCILED')
    def test_tolerance(self):self.assertEqual(classify(100,110),'RECONCILED')
    def test_review(self):self.assertEqual(classify(100,111),'REVIEW')
    def test_incomplete(self):self.assertEqual(classify(100,100,complete=False),'UNKNOWN')
    def test_bad_tol(self):self.assertEqual(classify(100,100,tolerance_usd=-1),'UNKNOWN')
    def test_nan(self):self.assertEqual(classify('NaN',100),'UNKNOWN')
    def test_inf(self):self.assertEqual(classify('Infinity',100),'UNKNOWN')
    def test_bool(self):self.assertEqual(classify(True,100),'UNKNOWN')
    def test_negative_realized(self):self.assertEqual(classify(100,-100),'REVIEW')
    def test_decimal(self):self.assertEqual(classify('100.01','100.02',tolerance_usd='0.01'),'RECONCILED')
if __name__=="__main__":unittest.main()
