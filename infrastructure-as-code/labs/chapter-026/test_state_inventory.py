import copy
import json
import unittest
from pathlib import Path
from state_inventory import inspect

ROOT = Path(__file__).parent
SAFE = json.loads((ROOT / "sample-safe-state.json").read_text(encoding="utf-8"))
UNSAFE = json.loads((ROOT / "sample-unsafe-state.json").read_text(encoding="utf-8"))
POLICY = json.loads((ROOT / "state-policy.json").read_text(encoding="utf-8"))

class StateInventoryTests(unittest.TestCase):
    def bad(self, fn):
        s = copy.deepcopy(SAFE); fn(s); self.assertTrue(inspect(s, POLICY)[1])
    def test_safe(self):
        meta, errors = inspect(SAFE, POLICY); self.assertFalse(errors); self.assertEqual(len(meta["resource_addresses"]), 3)
    def test_unsafe(self): self.assertTrue(inspect(UNSAFE, POLICY)[1])
    def test_negative_serial(self): self.bad(lambda s: s.update(serial=-1))
    def test_bool_serial(self): self.bad(lambda s: s.update(serial=True))
    def test_bad_lineage(self): self.bad(lambda s: s.update(lineage="bad"))
    def test_bad_version(self): self.bad(lambda s: s.update(version=5))
    def test_bool_version(self): self.bad(lambda s: s.update(version=True))
    def test_bad_terraform_version(self): self.bad(lambda s: s.update(terraform_version="unknown"))
    def test_secret_output_name(self): self.bad(lambda s: s["outputs"].update(api_token={"value":"unsafe"}))
    def test_password_output_name(self): self.bad(lambda s: s["outputs"].update(database_password={"value":"unsafe"}))
    def test_bad_type(self): self.bad(lambda s: s["resources"][0].update(type="aws_db_instance"))
    def test_bad_mode(self): self.bad(lambda s: s["resources"][0].update(mode="data"))
    def test_duplicate_address(self): self.bad(lambda s: s["resources"].append(copy.deepcopy(s["resources"][0])))
    def test_missing_database(self): self.bad(lambda s: s["resources"].pop(1))
    def test_missing_instances(self): self.bad(lambda s: s["resources"][0].update(instances=[]))
    def test_bad_resource(self): self.bad(lambda s: s["resources"].append(None))
    def test_bad_module_path(self): self.bad(lambda s: s["resources"][0].update(module=123))
    def test_missing_resources(self): self.bad(lambda s: s.pop("resources"))
    def test_missing_outputs(self): self.bad(lambda s: s.pop("outputs"))
    def test_invalid_schema(self): self.assertTrue(inspect([], POLICY)[1])
    def test_invalid_policy(self):
        p = copy.deepcopy(POLICY); p["allowed_resource_types"] = []; self.assertTrue(inspect(SAFE, p)[1])
    def test_metadata_redaction(self):
        s = copy.deepcopy(SAFE); s["resources"][0]["instances"][0]["attributes"]["password"] = "DO_NOT_PRINT"; meta, errors = inspect(s, POLICY); self.assertFalse(errors); self.assertNotIn("DO_NOT_PRINT", json.dumps(meta))

if __name__ == "__main__": unittest.main()
