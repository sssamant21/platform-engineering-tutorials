import copy,json,unittest
from pathlib import Path
from dr import assess
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/dr-safe.json').read_text())
UNSAFE=json.loads((ROOT/'fixtures/dr-unsafe.json').read_text())
class DRTests(unittest.TestCase):
    def bad(self,fn):
        e=copy.deepcopy(SAFE);fn(e);self.assertTrue(assess(e))
    def test_safe(self):self.assertEqual(assess(SAFE),[])
    def test_unsafe(self):self.assertTrue(assess(UNSAFE))
    def test_invalid(self):self.assertTrue(assess([]))
    def test_rpo_exceeded(self):self.bad(lambda e:e.update(replica_lag_minutes=20))
    def test_rto_exceeded(self):self.bad(lambda e:e.update(restore_duration_minutes=61))
    def test_backup_integrity(self):self.bad(lambda e:e.update(backup_integrity=False))
    def test_restore_drill_passed(self):self.bad(lambda e:e.update(restore_drill_passed=False))
    def test_fencing_verified(self):self.bad(lambda e:e.update(fencing_verified=False))
    def test_quorum_healthy(self):self.bad(lambda e:e.update(quorum_healthy=False))
    def test_dbre_approved(self):self.bad(lambda e:e.update(dbre_approved=False))
    def test_encryption_key_available(self):self.bad(lambda e:e.update(encryption_key_available=False))
    def test_invalid_rpo_minutes(self):self.bad(lambda e:e.update(rpo_minutes=-1))
    def test_invalid_rto_minutes(self):self.bad(lambda e:e.update(rto_minutes=-1))
    def test_invalid_replica_lag_minutes(self):self.bad(lambda e:e.update(replica_lag_minutes=-1))
    def test_invalid_restore_duration_minutes(self):self.bad(lambda e:e.update(restore_duration_minutes=-1))
if __name__=="__main__":unittest.main()
