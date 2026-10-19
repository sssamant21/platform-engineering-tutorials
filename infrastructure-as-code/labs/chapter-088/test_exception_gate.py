import json,unittest
from pathlib import Path
from exception_gate import assess
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/exception-safe.json').read_text())
class ExceptionTests(unittest.TestCase):
    def bad(self,**changes):self.assertTrue(assess(dict(SAFE,**changes)))
    def test_safe(self):self.assertEqual(assess(SAFE),[])
    def test_invalid(self):self.assertTrue(assess(None))
    def test_control(self):self.bad(control_id='')
    def test_resource(self):self.bad(resource='')
    def test_wildcard(self):self.bad(resource='*')
    def test_owner(self):self.bad(owner='')
    def test_approver(self):self.bad(approver='')
    def test_self_approval(self):self.bad(approver='sre')
    def test_reason(self):self.bad(reason='')
    def test_compensating(self):self.bad(compensating_control='')
    def test_expired(self):self.bad(expiry_day=99)
    def test_excessive(self):self.bad(expiry_day=131)
    def test_unapproved(self):self.bad(approved=False)
    def test_bad_now(self):self.assertTrue(assess(SAFE,now_day='100'))
if __name__=="__main__":unittest.main()
