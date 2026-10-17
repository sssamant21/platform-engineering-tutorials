import copy
import json
import unittest
from pathlib import Path
from governance import validate_inventory

EXAMPLE = json.loads((Path(__file__).parent / "environments.json").read_text(encoding="utf-8"))

class GovernanceTests(unittest.TestCase):
    def test_example_passes(self):
        self.assertEqual(validate_inventory(EXAMPLE), [])

    def test_duplicate_backend_denied(self):
        doc = copy.deepcopy(EXAMPLE)
        doc["stacks"][1]["backend_key"] = doc["stacks"][0]["backend_key"]
        self.assertTrue(any("duplicate backend" in e for e in validate_inventory(doc)))

    def test_prod_auto_apply_denied(self):
        doc = copy.deepcopy(EXAMPLE)
        doc["stacks"][1]["auto_apply"] = True
        self.assertTrue(any("auto_apply" in e for e in validate_inventory(doc)))

    def test_unencrypted_state_denied(self):
        doc = copy.deepcopy(EXAMPLE)
        doc["stacks"][1]["state"]["encrypted"] = False
        self.assertTrue(any("state must enable" in e for e in validate_inventory(doc)))

    def test_missing_owner_denied(self):
        doc = copy.deepcopy(EXAMPLE)
        doc["stacks"][0]["owner"] = ""
        self.assertTrue(any("invalid owner" in e for e in validate_inventory(doc)))

    def test_missing_dbre_approval_denied(self):
        doc = copy.deepcopy(EXAMPLE)
        doc["stacks"][1]["approvals"] = ["service-owner"]
        self.assertTrue(any("DBRE" in e for e in validate_inventory(doc)))

    def test_unknown_cloud_denied(self):
        doc = copy.deepcopy(EXAMPLE)
        doc["stacks"][0]["cloud"] = "unknown"
        self.assertTrue(any("unsupported cloud" in e for e in validate_inventory(doc)))

if __name__ == "__main__":
    unittest.main()
