import copy,json,unittest
from pathlib import Path
from governance_gate import validate
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/safe.json').read_text())
POLICY=json.loads((ROOT/'policy.json').read_text())
class GateTests(unittest.TestCase):
    def bad(self,fn):
        e=copy.deepcopy(SAFE);fn(e);self.assertTrue(validate(e,POLICY))
    def test_safe(self):self.assertEqual(validate(SAFE,POLICY),[])
    def test_unsafe(self):self.assertTrue(validate(json.loads((ROOT/'fixtures/unsafe.json').read_text()),POLICY))
    def test_invalid_evidence(self):self.assertTrue(validate([],POLICY))
    def test_invalid_policy(self):self.assertTrue(validate(SAFE,[]))
    def test_policy_version(self):
        p=copy.deepcopy(POLICY);p['schema_version']=2;self.assertTrue(validate(SAFE,p))
    def test_policy_tools(self):
        p=copy.deepcopy(POLICY);p['required_tools']=[];self.assertTrue(validate(SAFE,p))
    def test_policy_targets(self):
        p=copy.deepcopy(POLICY);p['targets']={};self.assertTrue(validate(SAFE,p))
    def test_policy_controls(self):
        p=copy.deepcopy(POLICY);p['required_controls']=[];self.assertTrue(validate(SAFE,p))
    def test_policy_exactness(self):
        p=copy.deepcopy(POLICY);p['require_exact_controls']=False;self.assertTrue(validate(SAFE,p))
    def test_schema(self):self.bad(lambda e:e.update(schema_version=2))
    def test_environment(self):self.bad(lambda e:e.update(environment='prod'))
    def test_tools(self):self.bad(lambda e:e.update(tools=['pulumi']))
    def test_missing_targets(self):self.bad(lambda e:e.pop('targets'))
    def test_owner(self):self.bad(lambda e:e.update(owner=''))
    def test_ticket(self):self.bad(lambda e:e.update(ticket='APPROVED'))
    def test_commit(self):self.bad(lambda e:e.update(commit=''))
    def test_preview_digest(self):self.bad(lambda e:e.update(preview_digest='invalid'))
    def test_missing_controls(self):self.bad(lambda e:e.pop('controls'))
    def test_extra_control(self):self.bad(lambda e:e['controls'].update(bypass=True))
    def test_target_pulumi(self):self.bad(lambda e:e['targets'].update(pulumi='production'))
    def test_target_cloudformation(self):self.bad(lambda e:e['targets'].update(cloudformation='production'))
    def test_target_bicep(self):self.bad(lambda e:e['targets'].update(bicep='production'))
    def test_control_signed_source(self):self.bad(lambda e:e['controls'].update(signed_source=False))
    def test_control_pinned_toolchain(self):self.bad(lambda e:e['controls'].update(pinned_toolchain=False))
    def test_control_oidc_scoped(self):self.bad(lambda e:e['controls'].update(oidc_scoped=False))
    def test_control_least_privilege(self):self.bad(lambda e:e['controls'].update(least_privilege=False))
    def test_control_preview_reviewed(self):self.bad(lambda e:e['controls'].update(preview_reviewed=False))
    def test_control_policy_enforced(self):self.bad(lambda e:e['controls'].update(policy_enforced=False))
    def test_control_approval_signed(self):self.bad(lambda e:e['controls'].update(approval_signed=False))
    def test_control_preview_digest_verified(self):self.bad(lambda e:e['controls'].update(preview_digest_verified=False))
    def test_control_commit_binding_verified(self):self.bad(lambda e:e['controls'].update(commit_binding_verified=False))
    def test_control_target_binding_verified(self):self.bad(lambda e:e['controls'].update(target_binding_verified=False))
    def test_control_no_destroy(self):self.bad(lambda e:e['controls'].update(no_destroy=False))
    def test_control_no_stateful_replacement(self):self.bad(lambda e:e['controls'].update(no_stateful_replacement=False))
    def test_control_state_backup_verified(self):self.bad(lambda e:e['controls'].update(state_backup_verified=False))
    def test_control_db_backup_verified(self):self.bad(lambda e:e['controls'].update(db_backup_verified=False))
    def test_control_restore_rehearsed(self):self.bad(lambda e:e['controls'].update(restore_rehearsed=False))
    def test_control_dbre_approved(self):self.bad(lambda e:e['controls'].update(dbre_approved=False))
    def test_control_canary_approved(self):self.bad(lambda e:e['controls'].update(canary_approved=False))
    def test_control_slo_healthy(self):self.bad(lambda e:e['controls'].update(slo_healthy=False))
    def test_control_audit_enabled(self):self.bad(lambda e:e['controls'].update(audit_enabled=False))
    def test_control_gitops_ownership_reviewed(self):self.bad(lambda e:e['controls'].update(gitops_ownership_reviewed=False))
if __name__=="__main__":unittest.main()
