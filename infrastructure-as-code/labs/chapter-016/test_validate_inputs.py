import copy
import json
import unittest
from pathlib import Path
from validate_inputs import parse, validate

ROOT = Path(__file__).parent
POLICY = json.loads((ROOT / "input-policy.json").read_text(encoding="utf-8"))

def fixture(name):
    return parse((ROOT / "environments" / f"{name}.tfvars").read_text(encoding="utf-8"))

class InputTests(unittest.TestCase):
    def test_dev_valid(self):
        values, errors = fixture("dev")
        self.assertEqual(errors + validate(values, POLICY), [])
    def test_prod_valid(self):
        values, errors = fixture("prod")
        self.assertEqual(errors + validate(values, POLICY), [])
    def test_prod_replicas_denied(self):
        values, _ = fixture("prod"); values["db_replicas"] = 1
        self.assertTrue(any("replica" in e for e in validate(values, POLICY)))
    def test_prod_encryption_denied(self):
        values, _ = fixture("prod"); values["db_encrypted"] = False
        self.assertTrue(any("encryption" in e for e in validate(values, POLICY)))
    def test_prod_backup_denied(self):
        values, _ = fixture("prod"); values["db_backup_enabled"] = False
        self.assertTrue(any("backup" in e for e in validate(values, POLICY)))
    def test_invalid_environment(self):
        values, _ = fixture("dev"); values["environment"] = "production"
        self.assertTrue(validate(values, POLICY))
    def test_missing_ticket(self):
        values, _ = fixture("dev"); values["change_ticket"] = ""
        self.assertTrue(validate(values, POLICY))
    def test_missing_owner(self):
        values, _ = fixture("dev"); values["owner"] = ""
        self.assertTrue(validate(values, POLICY))
    def test_duplicate_key(self):
        _, errors = parse('environment = "dev"\nenvironment = "prod"')
        self.assertTrue(any("duplicate" in e for e in errors))
    def test_unsupported_syntax(self):
        _, errors = parse('database = { encrypted = true }')
        self.assertTrue(any("unsupported" in e for e in errors))
    def test_fractional_number_rejected(self):
        _, errors = parse('replicas = 2.5')
        self.assertTrue(errors)

if __name__ == "__main__":
    unittest.main()
