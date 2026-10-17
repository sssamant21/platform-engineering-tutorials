import copy
import json
import unittest
from pathlib import Path
from backend_security import validate

ROOT = Path(__file__).parent
SAFE = json.loads((ROOT / "backend-inventory.json").read_text(encoding="utf-8"))
UNSAFE = json.loads((ROOT / "backend-inventory-unsafe.json").read_text(encoding="utf-8"))
POLICY = json.loads((ROOT / "backend-policy.json").read_text(encoding="utf-8"))

class BackendSecurityTests(unittest.TestCase):
    def bad(self, fn):
        d = copy.deepcopy(SAFE); fn(d); self.assertTrue(validate(d, POLICY))
    def test_safe(self): self.assertEqual(validate(SAFE, POLICY), [])
    def test_unsafe(self): self.assertTrue(validate(UNSAFE, POLICY))
    def test_local_prod(self): self.bad(lambda d: d["backends"][0].update(backend_type="local"))
    def test_public(self): self.bad(lambda d: d["backends"][0].update(public_access=True))
    def test_null_public(self): self.bad(lambda d: d["backends"][0].update(public_access=None))
    def test_wildcard(self): self.bad(lambda d: d["backends"][0].update(permissions=["*"]))
    def test_empty_permissions(self): self.bad(lambda d: d["backends"][0].update(permissions=[]))
    def test_static_identity(self): self.bad(lambda d: d["backends"][0].update(identity_ref="STATIC"))
    def test_missing_identity(self): self.bad(lambda d: d["backends"][0].pop("identity_ref"))
    def test_bad_environment(self): self.bad(lambda d: d["backends"][0].update(environment="production"))
    def test_bad_key(self): self.bad(lambda d: d["backends"][0].update(state_key="wrong/terraform.tfstate"))
    def test_duplicate_key(self): self.bad(lambda d: d["backends"][1].update(state_key=d["backends"][0]["state_key"]))
    def test_access_key(self): self.bad(lambda d: d["backends"][0].update(access_key="unsafe"))
    def test_missing_controls(self): self.bad(lambda d: d["backends"][0].pop("controls"))
    def test_encryption_off(self): self.bad(lambda d: d["backends"][0]["controls"].update(encryption=False))
    def test_versioning_off(self): self.bad(lambda d: d["backends"][0]["controls"].update(versioning=False))
    def test_locking_off(self): self.bad(lambda d: d["backends"][0]["controls"].update(locking=False))
    def test_tls_off(self): self.bad(lambda d: d["backends"][0]["controls"].update(tls=False))
    def test_audit_off(self): self.bad(lambda d: d["backends"][0]["controls"].update(audit_logging=False))
    def test_restore_off(self): self.bad(lambda d: d["backends"][0]["controls"].update(restore_tested=False))
    def test_empty_backends(self): self.bad(lambda d: d.update(backends=[]))
    def test_bad_entry(self): self.bad(lambda d: d["backends"].append(None))
    def test_bad_schema(self): self.assertTrue(validate([], POLICY))
    def test_policy_fail_open(self):
        p = copy.deepcopy(POLICY); p["require_private"] = False; self.assertTrue(validate(SAFE, p))
    def test_policy_no_controls(self):
        p = copy.deepcopy(POLICY); p["required_controls"] = []; self.assertTrue(validate(SAFE, p))

if __name__ == "__main__": unittest.main()
