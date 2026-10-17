import copy
import json
import unittest
from pathlib import Path
from state_ops_policy import validate

ROOT = Path(__file__).parent
SAFE = json.loads((ROOT / "sample-operations-safe.json").read_text(encoding="utf-8"))
UNSAFE = json.loads((ROOT / "sample-operations-unsafe.json").read_text(encoding="utf-8"))
PLAN = json.loads((ROOT / "sample-safe-plan.json").read_text(encoding="utf-8"))
DESTRUCTIVE = json.loads((ROOT / "sample-destructive-plan.json").read_text(encoding="utf-8"))
POLICY = json.loads((ROOT / "state-ops-policy.json").read_text(encoding="utf-8"))

class StateOpsPolicyTests(unittest.TestCase):
    def bad(self, fn):
        m = copy.deepcopy(SAFE); fn(m); self.assertTrue(validate(m, PLAN, POLICY))
    def bad_plan(self, fn):
        p = copy.deepcopy(PLAN); fn(p); self.assertTrue(validate(SAFE, p, POLICY))
    def test_safe(self): self.assertEqual(validate(SAFE, PLAN, POLICY), [])
    def test_unsafe(self): self.assertTrue(validate(UNSAFE, DESTRUCTIVE, POLICY))
    def test_destructive(self): self.assertTrue(validate(SAFE, DESTRUCTIVE, POLICY))
    def test_missing_ticket(self): self.bad(lambda m: m.update(change_ticket=""))
    def test_missing_backup(self): self.bad(lambda m: m.update(state_backup_verified=False))
    def test_missing_lock(self): self.bad(lambda m: m.update(exclusive_lock_verified=False))
    def test_bad_environment(self): self.bad(lambda m: m.update(environment="production"))
    def test_move_self(self): self.bad(lambda m: m["operations"][0].update(to="terraform_data.database"))
    def test_move_missing_source(self): self.bad(lambda m: m["operations"][0].update(**{"from":""}))
    def test_move_missing_owner(self): self.bad(lambda m: m["operations"][0].update(owner=""))
    def test_duplicate_target(self): self.bad(lambda m: m["operations"][1].update(to="terraform_data.primary_database"))
    def test_import_missing_id(self): self.bad(lambda m: m["operations"][1].update(object_id=""))
    def test_import_no_ownership(self): self.bad(lambda m: m["operations"][1].update(ownership_verified=False))
    def test_import_missing_owner(self): self.bad(lambda m: m["operations"][1].update(owner=""))
    def test_forget_destroy(self): self.bad(lambda m: m["operations"][2].update(destroy=True))
    def test_forget_missing_handoff(self): self.bad(lambda m: m["operations"][2].update(handoff_owner=""))
    def test_refresh_missing_address(self): self.bad(lambda m: m["operations"][3].update(address=""))
    def test_unknown_operation(self): self.bad(lambda m: m["operations"][0].update(operation="delete"))
    def test_empty_operations(self): self.bad(lambda m: m.update(operations=[]))
    def test_invalid_operation(self): self.bad(lambda m: m["operations"].append(None))
    def test_delete(self): self.bad_plan(lambda p: p["resource_changes"][0]["change"].update(actions=["delete"]))
    def test_reverse_replace(self): self.bad_plan(lambda p: p["resource_changes"][0]["change"].update(actions=["create","delete"]))
    def test_invalid_action(self): self.bad_plan(lambda p: p["resource_changes"][0]["change"].update(actions=["destroy"]))
    def test_bad_type(self): self.bad_plan(lambda p: p["resource_changes"][0].update(type="aws_db_instance"))
    def test_missing_address(self): self.bad_plan(lambda p: p["resource_changes"][0].update(address=""))
    def test_missing_changes(self): self.assertTrue(validate(SAFE, {}, POLICY))
    def test_bad_schema(self): self.assertTrue(validate([], PLAN, POLICY))
    def test_fail_open_policy(self):
        q = copy.deepcopy(POLICY); q["require_lock"] = False; self.assertTrue(validate(SAFE, PLAN, q))
    def test_noop_allowed(self):
        p = copy.deepcopy(PLAN); p["resource_changes"][0]["change"]["actions"] = ["no-op"]; self.assertEqual(validate(SAFE, p, POLICY), [])
    def test_create_allowed(self):
        p = copy.deepcopy(PLAN); p["resource_changes"][0]["change"]["actions"] = ["create"]; self.assertEqual(validate(SAFE, p, POLICY), [])

if __name__ == "__main__": unittest.main()
