import copy
import json
import unittest
from pathlib import Path
from expression_policy import validate

ROOT = Path(__file__).parent
POLICY = json.loads((ROOT / "expression-policy.json").read_text(encoding="utf-8"))
DEV = json.loads((ROOT / "environments/dev.json").read_text(encoding="utf-8"))
PROD = json.loads((ROOT / "environments/prod.json").read_text(encoding="utf-8"))

class ExpressionTests(unittest.TestCase):
    def test_dev(self): self.assertEqual(validate(DEV, POLICY), [])
    def test_prod(self): self.assertEqual(validate(PROD, POLICY), [])
    def test_environment(self):
        d=copy.deepcopy(DEV);d["environment"]="production";self.assertTrue(validate(d,POLICY))
    def test_owner(self):
        d=copy.deepcopy(DEV);d["owner"]="";self.assertTrue(validate(d,POLICY))
    def test_name(self):
        d=copy.deepcopy(DEV);d["service"]="INVALID";self.assertTrue(validate(d,POLICY))
    def test_empty_services(self):
        d=copy.deepcopy(DEV);d["services"]={};self.assertTrue(validate(d,POLICY))
    def test_duplicate_canonical_name(self):
        d=copy.deepcopy(DEV);d["services"]["API"]=d["services"]["api"];self.assertTrue(any("duplicate" in e for e in validate(d,POLICY)))
    def test_bad_replicas(self):
        d=copy.deepcopy(DEV);d["services"]["api"]["replicas"]=0;self.assertTrue(validate(d,POLICY))
    def test_prod_min_replicas(self):
        d=copy.deepcopy(PROD);d["services"]["api"]["replicas"]=2;self.assertTrue(any("production replica" in e for e in validate(d,POLICY)))
    def test_public_cidr(self):
        d=copy.deepcopy(DEV);d["network_cidr"]="8.8.8.0/24";self.assertTrue(validate(d,POLICY))
    def test_invalid_cidr(self):
        d=copy.deepcopy(DEV);d["network_cidr"]="not-cidr";self.assertTrue(validate(d,POLICY))
    def test_enabled_boolean(self):
        d=copy.deepcopy(DEV);d["services"]["api"]["enabled"]="yes";self.assertTrue(validate(d,POLICY))

if __name__=="__main__": unittest.main()
