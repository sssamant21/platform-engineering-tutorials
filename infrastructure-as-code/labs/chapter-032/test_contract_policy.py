import copy,json,unittest
from pathlib import Path
from contract_policy import validate
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/"fixtures/contract-safe.json").read_text())
UNSAFE=json.loads((ROOT/"fixtures/contract-unsafe.json").read_text())
PLAN=json.loads((ROOT/"fixtures/plan-safe.json").read_text())
DESTRUCTIVE=json.loads((ROOT/"fixtures/plan-destructive.json").read_text())
POLICY=json.loads((ROOT/"contract-policy.json").read_text())
class ContractPolicyTests(unittest.TestCase):
    def bad(self,fn):
        m=copy.deepcopy(SAFE);fn(m);self.assertTrue(validate(m,PLAN,POLICY))
    def bad_plan(self,fn):
        p=copy.deepcopy(PLAN);fn(p);self.assertTrue(validate(SAFE,p,POLICY))
    def test_safe(self):self.assertEqual(validate(SAFE,PLAN,POLICY),[])
    def test_unsafe(self):self.assertTrue(validate(UNSAFE,DESTRUCTIVE,POLICY))
    def test_destructive(self):self.assertTrue(validate(SAFE,DESTRUCTIVE,POLICY))
    def test_environment(self):self.bad(lambda m:m.update(environment="unknown"))
    def test_ticket(self):self.bad(lambda m:m.update(change_ticket=""))
    def test_empty_modules(self):self.bad(lambda m:m.update(modules=[]))
    def test_missing_module(self):self.bad(lambda m:m["modules"].pop(0))
    def test_duplicate_module(self):self.bad(lambda m:m["modules"][1].update(name="network"))
    def test_missing_owner(self):self.bad(lambda m:m["modules"][0].update(owner=""))
    def test_schema_version(self):self.bad(lambda m:m["modules"][0].update(schema_version=2))
    def test_schema_bool(self):self.bad(lambda m:m["modules"][0].update(schema_version=True))
    def test_missing_input(self):self.bad(lambda m:m["modules"][0].update(inputs=["environment"]))
    def test_missing_output(self):self.bad(lambda m:m["modules"][1].update(outputs=["id"]))
    def test_nullable(self):self.bad(lambda m:m["modules"][0].update(nullable_inputs=["environment"]))
    def test_no_nullable_list(self):self.bad(lambda m:m["modules"][0].pop("nullable_inputs"))
    def test_cycle(self):self.bad(lambda m:m["modules"][0].update(depends_on=["application"]))
    def test_unknown_dependency(self):self.bad(lambda m:m["modules"][0].update(depends_on=["unknown"]))
    def test_database_dependency(self):self.bad(lambda m:m["modules"][1].update(depends_on=[]))
    def test_application_dependency(self):self.bad(lambda m:m["modules"][2].update(depends_on=[]))
    def test_invalid_dependency(self):self.bad(lambda m:m["modules"][0].update(depends_on="network"))
    def test_prod_replicas(self):self.bad(lambda m:m["database"].update(replicas=1))
    def test_prod_backup(self):self.bad(lambda m:m["database"].update(backup_enabled=False))
    def test_prod_encryption(self):self.bad(lambda m:m["database"].update(encryption_enabled=False))
    def test_no_database(self):self.bad(lambda m:m.pop("database"))
    def test_delete(self):self.bad_plan(lambda p:p["resource_changes"][0]["change"].update(actions=["delete"]))
    def test_reverse_replace(self):self.bad_plan(lambda p:p["resource_changes"][0]["change"].update(actions=["create","delete"]))
    def test_bad_action(self):self.bad_plan(lambda p:p["resource_changes"][0]["change"].update(actions=["destroy"]))
    def test_unapproved_type(self):self.bad_plan(lambda p:p["resource_changes"][0].update(type="aws_db_instance"))
    def test_missing_plan(self):self.assertTrue(validate(SAFE,{},POLICY))
    def test_bad_manifest(self):self.assertTrue(validate([],PLAN,POLICY))
    def test_fail_open_policy(self):
        p=copy.deepcopy(POLICY);p["deny_destructive_actions"]=False;self.assertTrue(validate(SAFE,PLAN,p))
    def test_noop_allowed(self):
        p=copy.deepcopy(PLAN);p["resource_changes"][0]["change"]["actions"]=["no-op"];self.assertEqual(validate(SAFE,p,POLICY),[])
if __name__=="__main__":unittest.main()
