import json,unittest
from pathlib import Path
from dr_gate import assess
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/dr-safe.json').read_text())
class DRTests(unittest.TestCase):
    def bad(self,**changes):self.assertTrue(assess(dict(SAFE,**changes)))
    def test_safe(self):self.assertEqual(assess(SAFE),[])
    def test_invalid(self):self.assertTrue(assess(None))
    def test_backup(self):self.bad(backup_isolated=False)
    def test_restore(self):self.bad(restore_succeeded=False)
    def test_kms(self):self.bad(kms_decrypt_verified=False)
    def test_replication(self):self.bad(replication_healthy=False)
    def test_rpo(self):self.bad(rpo_minutes=16)
    def test_rto(self):self.bad(rto_minutes=61)
    def test_negative_rpo(self):self.bad(rpo_minutes=-1)
    def test_negative_rto(self):self.bad(rto_minutes=-1)
    def test_string_rpo(self):self.bad(rpo_minutes='5')
    def test_bool_rto(self):self.bad(rto_minutes=True)
if __name__=="__main__":unittest.main()
