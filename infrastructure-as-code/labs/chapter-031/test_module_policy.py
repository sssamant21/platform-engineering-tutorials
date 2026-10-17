import copy,json,unittest
from pathlib import Path
from module_policy import validate
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/"sample-modules-safe.json").read_text())
UNSAFE=json.loads((ROOT/"sample-modules-unsafe.json").read_text())
PLAN=json.loads((ROOT/"sample-plan-safe.json").read_text())
DESTRUCTIVE=json.loads((ROOT/"sample-plan-destructive.json").read_text())
POLICY=json.loads((ROOT/"module-policy.json").read_text())
class ModulePolicyTests(unittest.TestCase):
    def bad(self,fn):
        m=copy.deepcopy(SAFE);fn(m);self.assertTrue(validate(m,PLAN,POLICY))
    def bad_plan(self,fn):
        p=copy.deepcopy(PLAN);fn(p);self.assertTrue(validate(SAFE,p,POLICY))
    def test_safe(self):self.assertEqual(validate(SAFE,PLAN,POLICY),[])
    def test_unsafe(self):self.assertTrue(validate(UNSAFE,DESTRUCTIVE,POLICY))
    def test_destructive(self):self.assertTrue(validate(SAFE,DESTRUCTIVE,POLICY))
    def test_bad_environment(self):self.bad(lambda m:m.update(environment="invalid"))
    def test_missing_ticket(self):self.bad(lambda m:m.update(change_ticket=""))
    def test_missing_modules(self):self.bad(lambda m:m.update(modules=[]))
    def test_missing_network(self):self.bad(lambda m:m["modules"].pop(0))
    def test_duplicate_name(self):self.bad(lambda m:m["modules"][1].update(name="network"))
    def test_missing_owner(self):self.bad(lambda m:m["modules"][0].update(owner=""))
    def test_unpinned_source(self):self.bad(lambda m:m["modules"][0].update(source="git::https://example.com/network.git?ref=main"))
    def test_missing_input(self):self.bad(lambda m:m["modules"][0].update(inputs=["environment"]))
    def test_missing_output(self):self.bad(lambda m:m["modules"][1].update(outputs=["id"]))
    def test_cycle(self):self.bad(lambda m:m["modules"][0].update(depends_on=["application"]))
    def test_unknown_dependency(self):self.bad(lambda m:m["modules"][0].update(depends_on=["missing"]))
    def test_database_without_network(self):self.bad(lambda m:m["modules"][1].update(depends_on=[]))
    def test_application_without_database(self):self.bad(lambda m:m["modules"][2].update(depends_on=[]))
    def test_invalid_dependency(self):self.bad(lambda m:m["modules"][0].update(depends_on="network"))
    def test_prod_replicas(self):self.bad(lambda m:m["database"].update(replicas=1))
    def test_prod_backup(self):self.bad(lambda m:m["database"].update(backup_enabled=False))
    def test_prod_encryption(self):self.bad(lambda m:m["database"].update(encryption_enabled=False))
    def test_missing_database_controls(self):self.bad(lambda m:m.pop("database"))
    def test_delete(self):self.bad_plan(lambda p:p["resource_changes"][0]["change"].update(actions=["delete"]))
    def test_reverse_replace(self):self.bad_plan(lambda p:p["resource_changes"][0]["change"].update(actions=["create","delete"]))
    def test_unknown_action(self):self.bad_plan(lambda p:p["resource_changes"][0]["change"].update(actions=["destroy"]))
    def test_unapproved_type(self):self.bad_plan(lambda p:p["resource_changes"][0].update(type="aws_db_instance"))
    def test_missing_plan(self):self.assertTrue(validate(SAFE,{},POLICY))
    def test_bad_manifest(self):self.assertTrue(validate([],PLAN,POLICY))
    def test_fail_open_policy(self):
        p=copy.deepcopy(POLICY);p["deny_destructive_actions"]=False;self.assertTrue(validate(SAFE,PLAN,p))
    def test_noop_allowed(self):
        p=copy.deepcopy(PLAN);p["resource_changes"][0]["change"]["actions"]=["no-op"];self.assertEqual(validate(SAFE,p,POLICY),[])
if __name__=="__main__":unittest.main()
