import copy
import json
import unittest
from pathlib import Path
from validate_stacks import validate

EXAMPLE = json.loads((Path(__file__).parent / "stacks.json").read_text(encoding="utf-8"))

class StackPolicyTests(unittest.TestCase):
    def test_example_passes(self):
        self.assertEqual(validate(EXAMPLE), [])

    def test_duplicate_backend_denied(self):
        doc = copy.deepcopy(EXAMPLE)
        doc["stacks"][1]["backend_key"] = doc["stacks"][0]["backend_key"]
        self.assertTrue(any("duplicate backend_key" in e for e in validate(doc)))

    def test_prod_auto_apply_denied(self):
        doc = copy.deepcopy(EXAMPLE)
        doc["stacks"][1]["auto_apply"] = True
        self.assertTrue(any("production auto_apply" in e for e in validate(doc)))

    def test_missing_owner_denied(self):
        doc = copy.deepcopy(EXAMPLE)
        doc["stacks"][0]["owner"] = ""
        self.assertTrue(any("invalid owner" in e for e in validate(doc)))

    def test_missing_dbre_approval_denied(self):
        doc = copy.deepcopy(EXAMPLE)
        doc["stacks"][1]["approvals"] = ["service-owner"]
        self.assertTrue(any("DBRE approval" in e for e in validate(doc)))

    def test_unencrypted_state_denied(self):
        doc = copy.deepcopy(EXAMPLE)
        doc["stacks"][1]["state"]["encrypted"] = False
        self.assertTrue(any("state encryption" in e for e in validate(doc)))

    def test_invalid_cloud_denied(self):
        doc = copy.deepcopy(EXAMPLE)
        doc["stacks"][0]["cloud"] = "invalid"
        self.assertTrue(any("invalid cloud" in e for e in validate(doc)))

if __name__ == "__main__":
    unittest.main()
