import copy
import json
import unittest
from pathlib import Path
from defensive_policy import validate

ROOT = Path(__file__).parent
POLICY = json.loads((ROOT / "defensive-policy.json").read_text(encoding="utf-8"))
DEV = json.loads((ROOT / "environments/dev.json").read_text(encoding="utf-8"))
PROD = json.loads((ROOT / "environments/prod.json").read_text(encoding="utf-8"))

class DefensiveTests(unittest.TestCase):
    def test_dev(self): self.assertEqual(validate(DEV, POLICY), [])
    def test_prod(self): self.assertEqual(validate(PROD, POLICY), [])
    def test_invalid_environment(self):
        d=copy.deepcopy(DEV); d["environment"]="production"; self.assertTrue(validate(d,POLICY))
    def test_missing_owner(self):
        d=copy.deepcopy(DEV); d["owner"]=None; self.assertTrue(validate(d,POLICY))
    def test_missing_ticket(self):
        d=copy.deepcopy(DEV); d["change_ticket"]=""; self.assertTrue(validate(d,POLICY))
    def test_missing_backup(self):
        d=copy.deepcopy(PROD); del d["backup_enabled"]; self.assertTrue(validate(d,POLICY))
    def test_backup_false(self):
        d=copy.deepcopy(PROD); d["backup_enabled"]=False; self.assertTrue(validate(d,POLICY))
    def test_encryption_false(self):
        d=copy.deepcopy(PROD); d["encryption_enabled"]=False; self.assertTrue(validate(d,POLICY))
    def test_deletion_protection_false(self):
        d=copy.deepcopy(PROD); d["deletion_protection"]=False; self.assertTrue(validate(d,POLICY))
    def test_production_replicas(self):
        d=copy.deepcopy(PROD); d["replicas"]=2; self.assertTrue(validate(d,POLICY))
    def test_null_replicas(self):
        d=copy.deepcopy(PROD); d["replicas"]=None; self.assertTrue(validate(d,POLICY))
    def test_bool_replicas(self):
        d=copy.deepcopy(PROD); d["replicas"]=True; self.assertTrue(validate(d,POLICY))
    def test_nonboolean_backup(self):
        d=copy.deepcopy(PROD); d["backup_enabled"]="true"; self.assertTrue(validate(d,POLICY))
    def test_public_network(self):
        d=copy.deepcopy(DEV); d["network_cidr"]="8.8.8.0/24"; self.assertTrue(validate(d,POLICY))
    def test_invalid_network(self):
        d=copy.deepcopy(DEV); d["network_cidr"]="invalid"; self.assertTrue(validate(d,POLICY))
    def test_invalid_policy(self):
        p=copy.deepcopy(POLICY); p["min_production_replicas"]=1; self.assertTrue(validate(PROD,p))

if __name__=="__main__": unittest.main()
