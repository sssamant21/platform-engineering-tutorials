import unittest
from anomaly import classify
class AnomalyTests(unittest.TestCase):
    def test_ok(self):self.assertEqual(classify(110,100),'OK')
    def test_review(self):self.assertEqual(classify(160,100),'REVIEW')
    def test_exact(self):self.assertEqual(classify(150,100),'REVIEW')
    def test_low_absolute(self):self.assertEqual(classify(15,10),'OK')
    def test_incomplete(self):self.assertEqual(classify(160,100,complete=False),'UNKNOWN')
    def test_stale(self):self.assertEqual(classify(160,100,fresh=False),'UNKNOWN')
    def test_zero(self):self.assertEqual(classify(160,0),'UNKNOWN')
    def test_negative(self):self.assertEqual(classify(-1,100),'UNKNOWN')
    def test_bool(self):self.assertEqual(classify(True,100),'UNKNOWN')
    def test_nan(self):self.assertEqual(classify('NaN',100),'UNKNOWN')
    def test_infinite(self):self.assertEqual(classify('Infinity',100),'UNKNOWN')
    def test_bad_ratio(self):self.assertEqual(classify(160,100,ratio=1),'UNKNOWN')
    def test_bad_absolute(self):self.assertEqual(classify(160,100,absolute_usd=0),'UNKNOWN')
if __name__=="__main__":unittest.main()
