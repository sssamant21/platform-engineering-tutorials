import copy
import json
import unittest
from pathlib import Path
from capstone_policy import validate

ROOT = Path(__file__).parent
PLAN = json.loads((ROOT / "sample-plan.json").read_text(encoding="utf-8"))
POLICY = json.loads((ROOT / "change-policy.json").read_text(encoding="utf-8"))

class CapstoneTests(unittest.TestCase):
    def test_fixture_passes(self):
        self.assertEqual(validate(PLAN, POLICY), [])
    def test_missing_ticket(self):
        p = copy.deepcopy(POLICY); p["change_ticket"] = ""
        self.assertTrue(any("change_ticket" in e for e in validate(PLAN, p)))
    def test_missing_owner(self):
        p = copy.deepcopy(POLICY); p["owner"] = ""
        self.assertTrue(any("owner" in e for e in validate(PLAN, p)))
    def test_delete(self):
        d = copy.deepcopy(PLAN); d["resource_changes"][0]["change"]["actions"] = ["delete"]
        self.assertTrue(any("destructive" in e for e in validate(d, POLICY)))
    def test_replace(self):
        d = copy.deepcopy(PLAN); d["resource_changes"][0]["change"]["actions"] = ["delete", "create"]
        self.assertTrue(validate(d, POLICY))
    def test_prod_without_approval(self):
        p = copy.deepcopy(POLICY); p["environment"] = "prod"
        self.assertTrue(any("production approval" in e for e in validate(PLAN, p)))
    def test_prod_database_without_dbre(self):
        p = copy.deepcopy(POLICY); p.update(environment="prod", service_kind="database", production_approved=True)
        self.assertTrue(any("DBRE" in e for e in validate(PLAN, p)))
    def test_prod_database_approved(self):
        p = copy.deepcopy(POLICY); p.update(environment="prod", service_kind="database", production_approved=True, dbre_approved=True)
        self.assertEqual(validate(PLAN, p), [])
    def test_invalid_actions(self):
        d = copy.deepcopy(PLAN); d["resource_changes"][0]["change"]["actions"] = []
        self.assertTrue(validate(d, POLICY))
    def test_invalid_environment(self):
        p = copy.deepcopy(POLICY); p["environment"] = "unknown"
        self.assertTrue(validate(PLAN, p))
    def test_invalid_schema(self):
        self.assertTrue(validate({"resource_changes": "invalid"}, POLICY))

if __name__ == "__main__":
    unittest.main()
