import copy
import json
import unittest
from pathlib import Path
from validate_transformations import validate

ROOT = Path(__file__).parent
POLICY = json.loads((ROOT / "transformation-policy.json").read_text(encoding="utf-8"))
DEV = json.loads((ROOT / "environments/dev.json").read_text(encoding="utf-8"))
PROD = json.loads((ROOT / "environments/prod.json").read_text(encoding="utf-8"))

class TransformationTests(unittest.TestCase):
    def test_dev(self): self.assertEqual(validate(DEV, POLICY), [])
    def test_prod(self): self.assertEqual(validate(PROD, POLICY), [])
    def test_invalid_environment(self):
        d=copy.deepcopy(DEV); d["environment"]="production"; self.assertTrue(validate(d,POLICY))
    def test_missing_owner(self):
        d=copy.deepcopy(DEV); d["owner"]=""; self.assertTrue(validate(d,POLICY))
    def test_duplicate_zone(self):
        d=copy.deepcopy(DEV); d["zones"]=["a","a"]; self.assertTrue(any("duplicate" in e for e in validate(d,POLICY)))
    def test_invalid_zone(self):
        d=copy.deepcopy(DEV); d["zones"]=["invalid"]; self.assertTrue(validate(d,POLICY))
    def test_empty_zones(self):
        d=copy.deepcopy(DEV); d["zones"]=[]; self.assertTrue(validate(d,POLICY))
    def test_empty_services(self):
        d=copy.deepcopy(DEV); d["services"]={}; self.assertTrue(validate(d,POLICY))
    def test_duplicate_canonical_key(self):
        d=copy.deepcopy(DEV); d["services"]["API"]=copy.deepcopy(d["services"]["api"]); self.assertTrue(any("duplicate canonical" in e for e in validate(d,POLICY)))
    def test_bad_replica_count(self):
        d=copy.deepcopy(DEV); d["services"]["api"]["replicas"]=0; self.assertTrue(validate(d,POLICY))
    def test_prod_minimum(self):
        d=copy.deepcopy(PROD); d["services"]["api"]["replicas"]=2; self.assertTrue(any("production replica" in e for e in validate(d,POLICY)))
    def test_missing_tier(self):
        d=copy.deepcopy(DEV); d["services"]["api"]["tier"]=""; self.assertTrue(validate(d,POLICY))
    def test_all_disabled(self):
        d=copy.deepcopy(DEV); d["services"]["api"]["enabled"]=False; d["services"]["worker"]["enabled"]=False; self.assertTrue(validate(d,POLICY))
    def test_matrix_cap(self):
        d=copy.deepcopy(PROD); p=copy.deepcopy(POLICY); p["max_workloads"]=5; self.assertTrue(any("cap" in e for e in validate(d,p)))
    def test_invalid_schema(self): self.assertTrue(validate([], POLICY))

if __name__=="__main__": unittest.main()
