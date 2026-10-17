import copy
import json
import unittest
from pathlib import Path
from lifecycle_policy import validate

ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/"sample-safe-plan.json").read_text(encoding="utf-8"))
REPLACE=json.loads((ROOT/"sample-replace-plan.json").read_text(encoding="utf-8"))
POLICY=json.loads((ROOT/"lifecycle-policy.json").read_text(encoding="utf-8"))

class LifecyclePolicyTests(unittest.TestCase):
    def test_safe(self):self.assertEqual(validate(SAFE,POLICY),[])
    def test_replace(self):self.assertTrue(validate(REPLACE,POLICY))
    def test_delete(self):
        p=copy.deepcopy(SAFE);p["resource_changes"][0]["change"]["actions"]=["delete"];self.assertTrue(validate(p,POLICY))
    def test_reverse_replace(self):
        p=copy.deepcopy(SAFE);p["resource_changes"][0]["change"]["actions"]=["delete","create"];self.assertTrue(validate(p,POLICY))
    def test_update_allowed(self):
        p=copy.deepcopy(SAFE);p["resource_changes"][0]["change"]["actions"]=["update"];self.assertEqual(validate(p,POLICY),[])
    def test_update_denied(self):
        p=copy.deepcopy(SAFE);p["resource_changes"][0]["change"]["actions"]=["update"];q=copy.deepcopy(POLICY);q["allow_updates"]=False;self.assertTrue(validate(p,q))
    def test_noop(self):
        p=copy.deepcopy(SAFE);p["resource_changes"][0]["change"]["actions"]=["no-op"];self.assertEqual(validate(p,POLICY),[])
    def test_bad_action(self):
        p=copy.deepcopy(SAFE);p["resource_changes"][0]["change"]["actions"]=["destroy"];self.assertTrue(validate(p,POLICY))
    def test_empty_actions(self):
        p=copy.deepcopy(SAFE);p["resource_changes"][0]["change"]["actions"]=[];self.assertTrue(validate(p,POLICY))
    def test_missing_changes(self):self.assertTrue(validate({},POLICY))
    def test_bad_type(self):
        p=copy.deepcopy(SAFE);p["resource_changes"][0]["type"]="aws_db_instance";self.assertTrue(validate(p,POLICY))
    def test_missing_address(self):
        p=copy.deepcopy(SAFE);p["resource_changes"][0]["address"]="";self.assertTrue(validate(p,POLICY))
    def test_invalid_item(self):
        p=copy.deepcopy(SAFE);p["resource_changes"].append(None);self.assertTrue(validate(p,POLICY))
    def test_invalid_schema(self):self.assertTrue(validate([],POLICY))
    def test_policy_delete_disabled(self):
        q=copy.deepcopy(POLICY);q["deny_deletes"]=False;self.assertTrue(validate(SAFE,q))
    def test_policy_replace_disabled(self):
        q=copy.deepcopy(POLICY);q["deny_replacements"]=False;self.assertTrue(validate(SAFE,q))
    def test_policy_types_empty(self):
        q=copy.deepcopy(POLICY);q["allowed_resource_types"]=[];self.assertTrue(validate(SAFE,q))
    def test_invalid_update_policy(self):
        q=copy.deepcopy(POLICY);q["allow_updates"]="true";self.assertTrue(validate(SAFE,q))

if __name__=="__main__":unittest.main()
