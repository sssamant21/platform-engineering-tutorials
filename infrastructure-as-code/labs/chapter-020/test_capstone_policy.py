import copy
import json
import unittest
from pathlib import Path
from capstone_policy import validate

ROOT = Path(__file__).parent
POLICY = json.loads((ROOT / "capstone-policy.json").read_text(encoding="utf-8"))
PLAN = json.loads((ROOT / "sample-plan.json").read_text(encoding="utf-8"))
DEV = json.loads((ROOT / "environments/dev.json").read_text(encoding="utf-8"))
PROD = json.loads((ROOT / "environments/prod.json").read_text(encoding="utf-8"))

class CapstoneTests(unittest.TestCase):
    def test_dev(self): self.assertEqual(validate(DEV, PLAN, POLICY), [])
    def test_prod(self): self.assertEqual(validate(PROD, PLAN, POLICY), [])
    def test_environment(self):
        d=copy.deepcopy(DEV); d["environment"]="production"; self.assertTrue(validate(d,PLAN,POLICY))
    def test_owner(self):
        d=copy.deepcopy(DEV); d["owner"]=""; self.assertTrue(validate(d,PLAN,POLICY))
    def test_ticket(self):
        d=copy.deepcopy(DEV); d["change_ticket"]=""; self.assertTrue(validate(d,PLAN,POLICY))
    def test_duplicate_zones(self):
        d=copy.deepcopy(DEV); d["zones"]=["a","a"]; self.assertTrue(validate(d,PLAN,POLICY))
    def test_invalid_zone(self):
        d=copy.deepcopy(DEV); d["zones"]=["z"]; self.assertTrue(validate(d,PLAN,POLICY))
    def test_empty_services(self):
        d=copy.deepcopy(DEV); d["services"]={}; self.assertTrue(validate(d,PLAN,POLICY))
    def test_bad_service_replicas(self):
        d=copy.deepcopy(DEV); d["services"]["api"]["replicas"]=0; self.assertTrue(validate(d,PLAN,POLICY))
    def test_prod_service_replicas(self):
        d=copy.deepcopy(PROD); d["services"]["api"]["replicas"]=2; self.assertTrue(validate(d,PLAN,POLICY))
    def test_prod_db_replicas(self):
        d=copy.deepcopy(PROD); d["database"]["replicas"]=1; self.assertTrue(validate(d,PLAN,POLICY))
    def test_prod_backup(self):
        d=copy.deepcopy(PROD); d["database"]["backup_enabled"]=False; self.assertTrue(validate(d,PLAN,POLICY))
    def test_prod_encryption(self):
        d=copy.deepcopy(PROD); d["database"]["encrypted"]=False; self.assertTrue(validate(d,PLAN,POLICY))
    def test_prod_deletion_protection(self):
        d=copy.deepcopy(PROD); d["database"]["deletion_protection"]=False; self.assertTrue(validate(d,PLAN,POLICY))
    def test_null_backup(self):
        d=copy.deepcopy(PROD); d["database"]["backup_enabled"]=None; self.assertTrue(validate(d,PLAN,POLICY))
    def test_matrix_cap(self):
        p=copy.deepcopy(POLICY); p["max_workloads"]=5; self.assertTrue(validate(PROD,PLAN,p))
    def test_delete(self):
        p=copy.deepcopy(PLAN); p["resource_changes"][0]["change"]["actions"]=["delete"]; self.assertTrue(validate(DEV,p,POLICY))
    def test_replace(self):
        p=copy.deepcopy(PLAN); p["resource_changes"][0]["change"]["actions"]=["delete","create"]; self.assertTrue(validate(DEV,p,POLICY))
    def test_invalid_actions(self):
        p=copy.deepcopy(PLAN); p["resource_changes"][0]["change"]["actions"]=[]; self.assertTrue(validate(DEV,p,POLICY))
    def test_missing_resource_changes(self):
        p={}; self.assertTrue(validate(DEV,p,POLICY))
    def test_unsafe_policy(self):
        p=copy.deepcopy(POLICY); p["deny_deletes"]=False; self.assertTrue(validate(DEV,PLAN,p))
    def test_invalid_schema(self): self.assertTrue(validate([],PLAN,POLICY))

if __name__ == "__main__": unittest.main()
