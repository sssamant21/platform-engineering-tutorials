import copy
import unittest
from change_policy import validate_change

BASE = {
    "ticket": "CHG-004",
    "environment": "staging",
    "commit_sha": "a1b2c3d4",
    "owner": "platform-sre",
    "actions": ["update"],
    "approvals": ["platform-reviewer"],
    "rollback_plan": "Revert desired config, replan, review, apply",
    "verification": "Validate, output and SLO smoke tests"
}

class ChangePolicyTests(unittest.TestCase):
    def test_staging_approved(self):
        self.assertEqual(validate_change(BASE), [])

    def test_production_requires_owner(self):
        request = {**BASE, "environment": "prod"}
        self.assertTrue(validate_change(request))

    def test_prod_destructive_requires_separate_approval(self):
        request = {**BASE, "environment": "prod", "actions": ["replace"], "approvals": ["production-owner"]}
        self.assertTrue(validate_change(request))
        request["approvals"].append("destructive-change")
        self.assertEqual(validate_change(request), [])

    def test_unknown_action_fails_closed(self):
        self.assertTrue(validate_change({**BASE, "actions": ["erase-everything"]}))

    def test_invalid_sha(self):
        self.assertTrue(validate_change({**BASE, "commit_sha": "not-a-sha"}))

    def test_missing_rollback(self):
        self.assertTrue(validate_change({**BASE, "rollback_plan": ""}))

if __name__ == "__main__":
    unittest.main()
