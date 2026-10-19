import unittest
from cardinality_gate import assess
class CardinalityTests(unittest.TestCase):
    def test_valid(self):self.assertEqual(assess({'environment':3,'outcome':2}),([],6))
    def test_invalid(self):self.assertTrue(assess(None)[0])
    def test_empty(self):self.assertTrue(assess({})[0])
    def test_forbidden(self):self.assertTrue(assess({'resource_id':10})[0])
    def test_trace(self):self.assertTrue(assess({'trace_id':10})[0])
    def test_unknown(self):self.assertTrue(assess({'patient_id':10})[0])
    def test_over_budget(self):self.assertTrue(assess({'environment':100,'tool':100,'stage':100})[0])
    def test_bad_cardinality(self):self.assertTrue(assess({'environment':0})[0])
    def test_boolean(self):self.assertTrue(assess({'environment':True})[0])
    def test_negative_budget(self):self.assertTrue(assess({'environment':2},-1)[0])
    def test_bool_budget(self):self.assertTrue(assess({'environment':2},True)[0])
    def test_large_dimension(self):self.assertTrue(assess({'environment':1001})[0])
if __name__=="__main__":unittest.main()
