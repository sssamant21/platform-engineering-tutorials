import copy
import json
import unittest
from pathlib import Path
from capstone_policy import validate

ROOT = Path(__file__).parent
MANIFEST = json.loads((ROOT / "provider-manifest.json").read_text(encoding="utf-8"))
SAFE = json.loads((ROOT / "sample-safe-plan.json").read_text(encoding="utf-8"))
REPLACE = json.loads((ROOT / "sample-replacement-plan.json").read_text(encoding="utf-8"))
POLICY = json.loads((ROOT / "capstone-policy.json").read_text(encoding="utf-8"))

class CapstoneTests(unittest.TestCase):
    def bad_manifest(self, fn):
        m = copy.deepcopy(MANIFEST); fn(m); self.assertTrue(validate(m, SAFE, POLICY))
    def bad_plan(self, fn):
        p = copy.deepcopy(SAFE); fn(p); self.assertTrue(validate(MANIFEST, p, POLICY))
    def test_good(self): self.assertEqual(validate(MANIFEST, SAFE, POLICY), [])
    def test_replace(self): self.assertTrue(validate(MANIFEST, REPLACE, POLICY))
    def test_bad_source(self): self.bad_manifest(lambda m: m["providers"][0].update(source="evil/aws"))
    def test_wrong_region(self): self.bad_manifest(lambda m: m["providers"][0].update(region="unknown"))
    def test_bad_alias(self): self.bad_manifest(lambda m: m["providers"][0].update(alias="Bad Alias"))
    def test_duplicate_alias(self): self.bad_manifest(lambda m: m["providers"][1].update(alias="primary"))
    def test_static_identity(self): self.bad_manifest(lambda m: m["providers"][0].update(identity_ref="AKIAEXAMPLE"))
    def test_inline_key(self): self.bad_manifest(lambda m: m["providers"][0].update(access_key="bad"))
    def test_missing_ticket(self): self.bad_manifest(lambda m: m.update(change_ticket=""))
    def test_missing_owner(self): self.bad_manifest(lambda m: m.update(owner=""))
    def test_bad_environment(self): self.bad_manifest(lambda m: m.update(environment="production"))
    def test_empty_providers(self): self.bad_manifest(lambda m: m.update(providers=[]))
    def test_delete(self): self.bad_plan(lambda p: p["resource_changes"][0]["change"].update(actions=["delete"]))
    def test_reverse_replace(self): self.bad_plan(lambda p: p["resource_changes"][0]["change"].update(actions=["delete","create"]))
    def test_bad_action(self): self.bad_plan(lambda p: p["resource_changes"][0]["change"].update(actions=["destroy"]))
    def test_empty_actions(self): self.bad_plan(lambda p: p["resource_changes"][0]["change"].update(actions=[]))
    def test_bad_resource_type(self): self.bad_plan(lambda p: p["resource_changes"][0].update(type="aws_db_instance"))
    def test_missing_address(self): self.bad_plan(lambda p: p["resource_changes"][0].update(address=""))
    def test_missing_changes(self): self.assertTrue(validate(MANIFEST, {}, POLICY))
    def test_invalid_item(self): self.bad_plan(lambda p: p["resource_changes"].append(None))
    def test_policy_untrusted(self):
        q = copy.deepcopy(POLICY); q["allowed_provider_sources"] = []; self.assertTrue(validate(MANIFEST, SAFE, q))
    def test_policy_destructive(self):
        q = copy.deepcopy(POLICY); q["deny_deletes"] = False; self.assertTrue(validate(MANIFEST, SAFE, q))
    def test_invalid_schema(self): self.assertTrue(validate([], SAFE, POLICY))
    def test_update_allowed(self):
        p = copy.deepcopy(SAFE); p["resource_changes"][0]["change"]["actions"] = ["update"]; self.assertEqual(validate(MANIFEST, p, POLICY), [])
    def test_noop_allowed(self):
        p = copy.deepcopy(SAFE); p["resource_changes"][0]["change"]["actions"] = ["no-op"]; self.assertEqual(validate(MANIFEST, p, POLICY), [])

if __name__ == "__main__":
    unittest.main()
