import copy
import json
import unittest
from pathlib import Path
from provider_policy import validate

ROOT = Path(__file__).parent
POLICY = json.loads((ROOT / "provider-policy.json").read_text(encoding="utf-8"))
GOOD = json.loads((ROOT / "provider-manifest-good.json").read_text(encoding="utf-8"))
BAD = json.loads((ROOT / "provider-manifest-bad.json").read_text(encoding="utf-8"))

class ProviderPolicyTests(unittest.TestCase):
    def test_good(self): self.assertEqual(validate(GOOD,POLICY),[])
    def test_bad(self): self.assertTrue(validate(BAD,POLICY))
    def test_source(self):
        d=copy.deepcopy(GOOD);d["providers"][0]["source"]="evil/aws";self.assertTrue(validate(d,POLICY))
    def test_duplicate_alias(self):
        d=copy.deepcopy(GOOD);d["providers"][1]["alias"]="primary";self.assertTrue(any("duplicate" in e for e in validate(d,POLICY)))
    def test_invalid_alias(self):
        d=copy.deepcopy(GOOD);d["providers"][0]["alias"]="Bad Alias";self.assertTrue(validate(d,POLICY))
    def test_missing_ticket(self):
        d=copy.deepcopy(GOOD);d["change_ticket"]="";self.assertTrue(validate(d,POLICY))
    def test_missing_owner(self):
        d=copy.deepcopy(GOOD);d["owner"]="";self.assertTrue(validate(d,POLICY))
    def test_wrong_region(self):
        d=copy.deepcopy(GOOD);d["providers"][0]["region"]="moon";self.assertTrue(validate(d,POLICY))
    def test_inline_secret(self):
        d=copy.deepcopy(GOOD);d["providers"][0]["client_secret"]="unsafe";self.assertTrue(validate(d,POLICY))
    def test_identity(self):
        d=copy.deepcopy(GOOD);d["providers"][0]["identity_ref"]="static-key";self.assertTrue(validate(d,POLICY))
    def test_version(self):
        d=copy.deepcopy(GOOD);d["providers"][0]["constraint"]="latest";self.assertTrue(validate(d,POLICY))
    def test_empty_providers(self):
        d=copy.deepcopy(GOOD);d["providers"]=[];self.assertTrue(validate(d,POLICY))
    def test_invalid_environment(self):
        d=copy.deepcopy(GOOD);d["environment"]="production";self.assertTrue(validate(d,POLICY))
    def test_invalid_policy(self):
        p=copy.deepcopy(POLICY);p["allowed_sources"]=[];self.assertTrue(validate(GOOD,p))
    def test_unsafe_policy(self):
        p=copy.deepcopy(POLICY);p["require_prod_ticket"]=False;self.assertTrue(validate(GOOD,p))
    def test_invalid_schema(self): self.assertTrue(validate([],POLICY))

if __name__ == "__main__": unittest.main()
