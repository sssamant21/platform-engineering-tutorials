import copy
import json
import unittest
from pathlib import Path
from data_contract_policy import validate

ROOT=Path(__file__).parent
CONTRACT=json.loads((ROOT/"sample-contract.json").read_text(encoding="utf-8"))
POLICY=json.loads((ROOT/"data-contract-policy.json").read_text(encoding="utf-8"))

class DataContractTests(unittest.TestCase):
    def check_bad(self, transform):
        c=copy.deepcopy(CONTRACT);transform(c);self.assertTrue(validate(c,POLICY))
    def test_valid(self):self.assertEqual(validate(CONTRACT,POLICY),[])
    def test_bad_schema(self):self.check_bad(lambda c:c.update(schema_version=2))
    def test_bool_schema(self):self.check_bad(lambda c:c.update(schema_version=True))
    def test_bad_source(self):self.check_bad(lambda c:c.update(source_type="untrusted-script"))
    def test_bad_environment(self):self.check_bad(lambda c:c.update(environment="production"))
    def test_missing_owner(self):self.check_bad(lambda c:c.update(owner=""))
    def test_missing_ticket(self):self.check_bad(lambda c:c.update(change_ticket=""))
    def test_missing_identity(self):self.check_bad(lambda c:c.update(source_identity=None))
    def test_missing_subnet(self):self.check_bad(lambda c:c["subnets"].pop("primary"))
    def test_invalid_subnet(self):self.check_bad(lambda c:c["subnets"].update(primary="bad"))
    def test_duplicate_subnets(self):self.check_bad(lambda c:c["subnets"].update(primary=c["subnets"]["secondary"]))
    def test_missing_database(self):self.check_bad(lambda c:c.pop("database"))
    def test_missing_db_name(self):self.check_bad(lambda c:c["database"].update(name=""))
    def test_prod_backup_false(self):self.check_bad(lambda c:c["database"].update(backup_enabled=False))
    def test_prod_encryption_false(self):self.check_bad(lambda c:c["database"].update(encrypted=False))
    def test_null_backup(self):self.check_bad(lambda c:c["database"].update(backup_enabled=None))
    def test_secret_key(self):self.check_bad(lambda c:c.update(api_token="unsafe"))
    def test_nested_secret_key(self):self.check_bad(lambda c:c["database"].update(password="unsafe"))
    def test_unsafe_policy(self):
        p=copy.deepcopy(POLICY);p["require_prod_backup"]=False;self.assertTrue(validate(CONTRACT,p))
    def test_invalid_schema(self):self.assertTrue(validate([],POLICY))

if __name__=="__main__":unittest.main()
