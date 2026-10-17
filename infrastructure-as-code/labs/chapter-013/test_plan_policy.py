import copy
import json
import unittest
from pathlib import Path
from plan_policy import validate

ROOT = Path(__file__).parent
PLAN = json.loads((ROOT / "sample-plan.json").read_text(encoding="utf-8"))
POLICY = json.loads((ROOT / "plan-policy.json").read_text(encoding="utf-8"))

class PlanPolicyTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate(PLAN, POLICY), [])
    def test_delete_denied(self):
        d = copy.deepcopy(PLAN)
        d["resource_changes"][0]["change"]["actions"] = ["delete"]
        self.assertTrue(any("destructive" in e for e in validate(d, POLICY)))
    def test_replace_denied(self):
        d = copy.deepcopy(PLAN)
        d["resource_changes"][0]["change"]["actions"] = ["delete", "create"]
        self.assertTrue(validate(d, POLICY))
    def test_missing_actions_denied(self):
        d = copy.deepcopy(PLAN)
        d["resource_changes"][0]["change"]["actions"] = []
        self.assertTrue(any("actions" in e for e in validate(d, POLICY)))
    def test_prod_approval_required(self):
        p = copy.deepcopy(POLICY)
        p["environment"] = "prod"
        self.assertTrue(any("approval" in e for e in validate(PLAN, p)))
    def test_prod_approved(self):
        p = copy.deepcopy(POLICY)
        p.update(environment="prod", production_approved=True)
        self.assertEqual(validate(PLAN, p), [])
    def test_no_change_mode(self):
        p = copy.deepcopy(POLICY)
        p["require_no_changes"] = True
        self.assertTrue(any("no-change" in e for e in validate(PLAN, p)))
    def test_noop_passes_strict(self):
        d = copy.deepcopy(PLAN)
        for item in d["resource_changes"]:
            item["change"]["actions"] = ["no-op"]
        p = copy.deepcopy(POLICY)
        p["require_no_changes"] = True
        self.assertEqual(validate(d, p), [])
    def test_malformed_plan(self):
        self.assertTrue(validate({"resource_changes": "invalid"}, POLICY))
    def test_unknown_action_denied(self):
        d = copy.deepcopy(PLAN)
        d["resource_changes"][0]["change"]["actions"] = ["surprise"]
        self.assertTrue(validate(d, POLICY))

if __name__ == "__main__":
    unittest.main()
