import unittest
from anomaly import classify
class AnomalyTests(unittest.TestCase):
    def test_normal(self):self.assertEqual(classify(12,10),'OK')
    def test_review(self):self.assertEqual(classify(20,10),'REVIEW')
    def test_threshold(self):self.assertEqual(classify(15,10),'REVIEW')
    def test_low(self):self.assertEqual(classify(5,1),'OK')
    def test_incomplete(self):self.assertEqual(classify(20,10,complete=False),'UNKNOWN')
    def test_stale(self):self.assertEqual(classify(20,10,fresh=False),'UNKNOWN')
    def test_zero_baseline(self):self.assertEqual(classify(20,0),'UNKNOWN')
    def test_negative(self):self.assertEqual(classify(-1,10),'UNKNOWN')
    def test_boolean(self):self.assertEqual(classify(True,10),'UNKNOWN')
    def test_nan(self):self.assertEqual(classify(float('nan'),10),'UNKNOWN')
    def test_infinite(self):self.assertEqual(classify(float('inf'),10),'UNKNOWN')
    def test_bad_ratio(self):self.assertEqual(classify(20,10,threshold_ratio=1),'UNKNOWN')
    def test_bad_min(self):self.assertEqual(classify(20,10,minimum_usd=0),'UNKNOWN')
if __name__=="__main__":unittest.main()
