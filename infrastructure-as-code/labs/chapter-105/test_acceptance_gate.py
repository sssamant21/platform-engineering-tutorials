import unittest
from dataclasses import replace
from acceptance_gate import Acceptance, assess

class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.good=Acceptance("payments",15,5,60,25,
            True,True,True,True,True,True,True,True,True,True,True,True)
    def test_valid(self):
        self.assertEqual(assess(self.good)["score"],100)
        self.assertEqual(assess(self.good)["decision"],"REVIEW_READY")
    def test_all_mandatory_fail_closed(self):
        mandatory=("immutable_copy_verified","independent_keys_verified",
                   "state_restore_verified","database_integrity_verified",
                   "old_primary_fenced","quorum_verified","business_transaction_verified",
                   "evidence_complete","sre_signed","dbre_signed")
        for field in mandatory:
            with self.subTest(field=field):
                self.assertEqual(assess(replace(self.good,**{field:False}))["decision"],"NO_GO")
    def test_rpo_breach(self):
        self.assertIn("rpo",assess(replace(self.good,rpo_observed_minutes=16))["failed"])
    def test_rto_breach(self):
        self.assertIn("rto",assess(replace(self.good,rto_observed_minutes=61))["failed"])
    def test_score_threshold(self):
        e=replace(self.good,kubernetes_restore_verified=False,rollback_verified=False)
        self.assertEqual(assess(e)["score"],85)
        self.assertEqual(assess(e)["decision"],"NO_GO")
    def test_negative_time(self):
        with self.assertRaises(ValueError):
            assess(replace(self.good,rpo_target_minutes=-1))
if __name__=="__main__":
    unittest.main()
