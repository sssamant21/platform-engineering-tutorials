import unittest
from dataclasses import replace
from finops_gate import Candidate,reconcile,gate
class GateTests(unittest.TestCase):
    def setUp(self):
        self.safe=Candidate(20000,60,40,0.5,True,True,True,True,True,True)
    def test_reconcile(self):
        self.assertTrue(reconcile([{"id":"a","owner":"team","cents":100}],100))
    def test_mismatch(self):
        self.assertFalse(reconcile([{"id":"a","owner":"team","cents":100}],200))
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            reconcile([{"id":"a","owner":"x","cents":1},{"id":"a","owner":"y","cents":2}],3)
    def test_safe(self):
        self.assertEqual(gate(self.safe)["decision"],"STAGING_ONLY")
    def test_all_controls_fail_closed(self):
        cases={"savings":0,"p99_cpu":90,"failover_headroom":5,"slo_burn":2,
               "backup_ok":False,"restore_ok":False,"rollback_ok":False,
               "finance_ok":False,"sre_ok":False,"dbre_ok":False}
        for field,value in cases.items():
            with self.subTest(field=field):
                self.assertEqual(gate(replace(self.safe,**{field:value}))["decision"],"BLOCK")
if __name__=="__main__":
    unittest.main()
