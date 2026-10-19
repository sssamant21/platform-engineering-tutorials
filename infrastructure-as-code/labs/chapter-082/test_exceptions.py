import unittest
from datetime import datetime,timezone,timedelta
from exceptions import assess
NOW=datetime(2026,10,19,tzinfo=timezone.utc)
SAFE=dict(control_id='deny_destroy',resource='db-lab',ticket='CHG-082',reason='testing',approver='security',requester='sre',compensating_control='isolated backup',environment='staging',scope='db-lab',expires_at='2026-10-20T00:00:00Z')
class ExceptionTests(unittest.TestCase):
    def check(self,**changes):
        e=dict(SAFE,**changes);self.assertTrue(assess([e],NOW))
    def test_empty(self):self.assertEqual(assess([],NOW),[])
    def test_safe(self):self.assertEqual(assess([SAFE],NOW),[])
    def test_invalid(self):self.assertTrue(assess(None,NOW))
    def test_invalid_item(self):self.assertTrue(assess([None],NOW))
    def test_self_approval(self):self.check(approver='sre')
    def test_blank_owner(self):self.check(approver='')
    def test_blank_reason(self):self.check(reason='')
    def test_blank_resource(self):self.check(resource='')
    def test_blank_control(self):self.check(control_id='')
    def test_blank_compensating(self):self.check(compensating_control='')
    def test_blank_ticket(self):self.check(ticket='')
    def test_blank_requester(self):self.check(requester='')
    def test_expired(self):self.check(expires_at='2026-10-18T00:00:00Z')
    def test_naive(self):self.check(expires_at='2026-10-20T00:00:00')
    def test_bad_expiry(self):self.check(expires_at='never')
    def test_blanket_production(self):self.check(environment='production',scope='*')
if __name__=="__main__":unittest.main()
