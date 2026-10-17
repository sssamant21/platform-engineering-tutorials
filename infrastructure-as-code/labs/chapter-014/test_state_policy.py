import copy
import json
import unittest
from pathlib import Path
from state_policy import validate

ROOT = Path(__file__).parent
STATE = json.loads((ROOT / "sample-state.json").read_text(encoding="utf-8"))
POLICY = json.loads((ROOT / "state-policy.json").read_text(encoding="utf-8"))

def clone():
    return copy.deepcopy(STATE), copy.deepcopy(POLICY)

class StatePolicyTests(unittest.TestCase):
    def test_fixture_passes(self):
        self.assertEqual(validate(STATE, POLICY), [])
    def test_missing_expected(self):
        s, p = clone()
        s["values"]["root_module"]["resources"].pop()
        self.assertTrue(any("missing expected" in e for e in validate(s, p)))
    def test_unexpected_resource(self):
        s, p = clone()
        r = copy.deepcopy(s["values"]["root_module"]["resources"][0])
        r["address"] = "terraform_data.unexpected"
        s["values"]["root_module"]["resources"].append(r)
        self.assertTrue(any("unexpected" in e for e in validate(s, p)))
    def test_duplicate_address(self):
        s, p = clone()
        s["values"]["root_module"]["resources"].append(copy.deepcopy(s["values"]["root_module"]["resources"][0]))
        self.assertTrue(any("duplicate address" in e for e in validate(s, p)))
    def test_missing_owner(self):
        s, p = clone()
        s["values"]["root_module"]["resources"][0]["values"]["input"].pop("owner")
        self.assertTrue(any("missing owner" in e for e in validate(s, p)))
    def test_wrong_environment(self):
        s, p = clone()
        s["values"]["root_module"]["resources"][0]["values"]["input"]["environment"] = "prod"
        self.assertTrue(any("environment mismatch" in e for e in validate(s, p)))
    def test_missing_schema(self):
        self.assertTrue(validate({"serial": 1}, POLICY))
    def test_nested_module(self):
        s, p = clone()
        r = s["values"]["root_module"]["resources"].pop()
        r["address"] = 'module.example.terraform_data.service["worker"]'
        s["values"]["root_module"]["child_modules"] = [{"address": "module.example", "resources": [r]}]
        p["expected_addresses"][-1] = r["address"]
        self.assertEqual(validate(s, p), [])
    def test_bad_expected_addresses(self):
        s, p = clone()
        p["expected_addresses"] = []
        self.assertTrue(validate(s, p))
    def test_invalid_module_resources(self):
        s, p = clone()
        s["values"]["root_module"]["resources"] = "invalid"
        self.assertTrue(validate(s, p))

if __name__ == "__main__":
    unittest.main()
