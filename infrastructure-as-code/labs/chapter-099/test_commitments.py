import unittest
from commitments import model
class CommitmentTests(unittest.TestCase):
    def test_valid(self):self.assertTrue(model(1000,700,80)['break_even'])
    def test_loss(self):self.assertFalse(model(1000,900,80)['break_even'])
    def test_utilized(self):self.assertEqual(model(1000,700,80)['utilized_equivalent_usd'],'800.00')
    def test_net(self):self.assertEqual(model(1000,700,80)['illustrative_net_usd'],'100.00')
    def test_zero_eligible(self):self.assertIsNone(model(0,10,50))
    def test_negative(self):self.assertIsNone(model(100,-1,50))
    def test_over_util(self):self.assertIsNone(model(100,10,101))
    def test_negative_util(self):self.assertIsNone(model(100,10,-1))
    def test_nan(self):self.assertIsNone(model('NaN',10,50))
    def test_bool(self):self.assertIsNone(model(True,10,50))
if __name__=="__main__":unittest.main()
