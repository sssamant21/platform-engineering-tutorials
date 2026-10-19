import copy,json,unittest
from pathlib import Path
from datetime import datetime,timezone
from findings import assess
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/findings-safe.json').read_text())
UNSAFE=json.loads((ROOT/'fixtures/findings-unsafe.json').read_text())
NOW=datetime(2026,10,19,tzinfo=timezone.utc)
SUP=dict(id='SYN-3',severity='medium',owner='SRE',fingerprint='synthetic',status='suppressed',approver='security',reason='test',expires_at='2026-10-20T00:00:00Z')
class FindingTests(unittest.TestCase):
    def check(self,**changes):self.assertTrue(assess([dict(SUP,**changes)],NOW))
    def test_safe(self):self.assertEqual(assess(SAFE,NOW),[])
    def test_unsafe(self):self.assertTrue(assess(UNSAFE,NOW))
    def test_invalid(self):self.assertTrue(assess(None,NOW))
    def test_invalid_item(self):self.assertTrue(assess([None],NOW))
    def test_safe_suppression(self):self.assertEqual(assess([SUP],NOW),[])
    def test_self_approval(self):self.check(approver='SRE')
    def test_blank_approval(self):self.check(approver='')
    def test_blank_reason(self):self.check(reason='')
    def test_expired(self):self.check(expires_at='2026-10-18T00:00:00Z')
    def test_naive(self):self.check(expires_at='2026-10-20T00:00:00')
    def test_bad_date(self):self.check(expires_at='never')
    def test_invalid_severity(self):self.check(severity='severe')
    def test_invalid_status(self):self.check(status='ignored')
    def test_missing_fingerprint(self):self.check(fingerprint='')
    def test_critical_suppressed(self):self.check(severity='critical')
if __name__=="__main__":unittest.main()
