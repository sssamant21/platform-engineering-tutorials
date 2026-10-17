import copy
import json
import unittest
from pathlib import Path
from state_dr_policy import validate
from snapshot_manifest import inspect

ROOT = Path(__file__).parent
SAFE = json.loads((ROOT / "sample-dr-safe.json").read_text(encoding="utf-8"))
UNSAFE = json.loads((ROOT / "sample-dr-unsafe.json").read_text(encoding="utf-8"))
STATE = json.loads((ROOT / "sample-state.json").read_text(encoding="utf-8"))
POLICY = json.loads((ROOT / "dr-policy.json").read_text(encoding="utf-8"))

class StateDRPolicyTests(unittest.TestCase):
    def bad(self, fn):
        m = copy.deepcopy(SAFE); fn(m); self.assertTrue(validate(m, STATE, POLICY))
    def test_safe(self): self.assertEqual(validate(SAFE, STATE, POLICY), [])
    def test_unsafe(self): self.assertTrue(validate(UNSAFE, STATE, POLICY))
    def test_no_ticket(self): self.bad(lambda m: m.update(change_ticket=""))
    def test_bad_environment(self): self.bad(lambda m: m.update(environment="production"))
    def test_same_backend(self): self.bad(lambda m: m.update(destination_backend=m["source_backend"]))
    def test_missing_source(self): self.bad(lambda m: m.update(source_backend=""))
    def test_missing_snapshot(self): self.bad(lambda m: m.update(snapshot_id=""))
    def test_bad_sha(self): self.bad(lambda m: m.update(snapshot_sha256="bad"))
    def test_wrong_lineage(self): self.bad(lambda m: m.update(snapshot_lineage="wrong"))
    def test_wrong_serial(self): self.bad(lambda m: m.update(snapshot_serial=8))
    def test_negative_serial(self): self.bad(lambda m: m.update(snapshot_serial=-1))
    def test_low_retention(self): self.bad(lambda m: m.update(retention_days=1))
    def test_bad_rpo(self): self.bad(lambda m: m.update(rpo_minutes=61))
    def test_bad_rto(self): self.bad(lambda m: m.update(rto_minutes=241))
    def test_zero_rpo(self): self.bad(lambda m: m.update(rpo_minutes=0))
    def test_encryption_off(self): self.bad(lambda m: m["controls"].update(encrypted=False))
    def test_versioning_off(self): self.bad(lambda m: m["controls"].update(versioned=False))
    def test_lock_off(self): self.bad(lambda m: m["controls"].update(lock_verified=False))
    def test_freeze_off(self): self.bad(lambda m: m["controls"].update(writers_frozen=False))
    def test_restore_off(self): self.bad(lambda m: m["controls"].update(restore_tested=False))
    def test_integrity_off(self): self.bad(lambda m: m["controls"].update(integrity_verified=False))
    def test_missing_controls(self): self.bad(lambda m: m.pop("controls"))
    def test_bad_schema(self): self.assertTrue(validate([], STATE, POLICY))
    def test_bad_state_version(self):
        s = copy.deepcopy(STATE); s["version"] = 5; self.assertTrue(validate(SAFE, s, POLICY))
    def test_bad_policy(self):
        p = copy.deepcopy(POLICY); p["require_prod_ticket"] = False; self.assertTrue(validate(SAFE, STATE, p))
    def test_snapshot_metadata(self):
        m = inspect(ROOT / "sample-state.json"); self.assertEqual(m["serial"], 7); self.assertEqual(m["resource_count"], 2)
    def test_snapshot_digest_length(self): self.assertEqual(len(inspect(ROOT / "sample-state.json")["sha256"]), 64)

if __name__ == "__main__": unittest.main()
