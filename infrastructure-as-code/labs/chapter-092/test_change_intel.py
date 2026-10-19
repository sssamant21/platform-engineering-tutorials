import json,unittest
from pathlib import Path
from change_intel import assess
SAFE=json.loads((Path(__file__).parent/'fixtures/change-safe.json').read_text())
class ChangeTests(unittest.TestCase):
    def bad(self,**changes):self.assertTrue(assess(dict(SAFE,**changes)))
    def test_valid(self):self.assertEqual(assess(SAFE),[])
    def test_invalid(self):self.assertTrue(assess(None))
    def test_ticket(self):self.bad(ticket='NO')
    def test_commit(self):self.bad(commit='unknown')
    def test_approved_commit(self):self.bad(approved_commit='unknown')
    def test_mismatch(self):self.bad(approved_commit='fedcba9876543210')
    def test_actor(self):self.bad(actor='other')
    def test_policy(self):self.bad(policy_version='v2')
    def test_skew(self):self.bad(time_skew_minutes=20)
    def test_skew_negative(self):self.bad(time_skew_minutes=-1)
    def test_exception(self):self.bad(exception_valid=False)
    def test_boolean(self):self.bad(time_skew_minutes=True)
if __name__=="__main__":unittest.main()
