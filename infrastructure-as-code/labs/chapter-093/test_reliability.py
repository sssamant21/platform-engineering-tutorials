import unittest
from reliability import assess
SAFE=[{'change_id':'a','failed':False},{'change_id':'b','failed':True}]
class ReliabilityTests(unittest.TestCase):
    def test_valid(self):
        errors,out=assess(SAFE,10000,5);self.assertEqual(errors,[]);self.assertEqual(out['change_failure_rate'],0.5)
    def test_budget(self):self.assertGreater(assess(SAFE,10000,20)[1]['error_budget_consumed'],1)
    def test_empty(self):self.assertTrue(assess([],100,1)[0])
    def test_duplicate(self):self.assertTrue(assess(SAFE+[SAFE[0]],100,1)[0])
    def test_missing_id(self):self.assertTrue(assess([{'failed':True}],100,1)[0])
    def test_failed_type(self):self.assertTrue(assess([{'change_id':'a','failed':1}],100,1)[0])
    def test_requests_zero(self):self.assertTrue(assess(SAFE,0,0)[0])
    def test_requests_bool(self):self.assertTrue(assess(SAFE,True,0)[0])
    def test_errors_bool(self):self.assertTrue(assess(SAFE,100,False)[0])
    def test_errors_excess(self):self.assertTrue(assess(SAFE,100,101)[0])
    def test_objective_zero(self):self.assertTrue(assess(SAFE,100,1,0)[0])
    def test_objective_one(self):self.assertTrue(assess(SAFE,100,1,1)[0])
    def test_nan(self):self.assertTrue(assess(SAFE,100,1,float('nan'))[0])
if __name__=="__main__":unittest.main()
