import copy,json,unittest
from pathlib import Path
from gate import validate,REQUIRED,STAGES,TARGETS
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/safe.json').read_text())
POLICY=json.loads((ROOT/'policy.json').read_text())
class GateTests(unittest.TestCase):
    def bad(self,fn):
        e=copy.deepcopy(SAFE);fn(e);self.assertTrue(validate(e,POLICY))
    def test_safe(self):self.assertEqual(validate(SAFE,POLICY),[])
    def test_unsafe(self):self.assertTrue(validate(json.loads((ROOT/'fixtures/unsafe.json').read_text()),POLICY))
    def test_non_dict_evidence(self):self.assertTrue(validate([],POLICY))
    def test_non_dict_policy(self):self.assertTrue(validate(SAFE,[]))
    def test_policy_controls_tamper(self):
        p=copy.deepcopy(POLICY);p['required_controls']=[];self.assertTrue(validate(SAFE,p))
    def test_policy_stages_tamper(self):
        p=copy.deepcopy(POLICY);p['stages']=[];self.assertTrue(validate(SAFE,p))
    def test_policy_targets_tamper(self):
        p=copy.deepcopy(POLICY);p['targets']={};self.assertTrue(validate(SAFE,p))
    def test_missing_controls_map(self):self.bad(lambda e:e.pop('controls'))
    def test_wrong_stage_order(self):self.bad(lambda e:e.update(stages=list(reversed(STAGES))))
    def test_missing_stage(self):self.bad(lambda e:e.update(stages=list(STAGES[:-1])))
    def test_extra_stage(self):self.bad(lambda e:e.update(stages=list(STAGES)+['destroy']))
    def test_placeholder_ticket(self):self.bad(lambda e:e.update(change_ticket='APPROVED'))
    def test_placeholder_digest(self):self.bad(lambda e:e.update(plan_digest='unverified'))
    def test_target_environment(self):self.bad(lambda e:e.update(environment='production'))
    def test_target_stack(self):self.bad(lambda e:e.update(stack='production'))
    def test_target_cloud_account(self):self.bad(lambda e:e.update(cloud_account='production'))
    def test_target_backend(self):self.bad(lambda e:e.update(backend='production'))
    def test_missing_owner(self):self.bad(lambda e:e.update(owner=''))
    def test_missing_change_ticket(self):self.bad(lambda e:e.update(change_ticket=''))
    def test_missing_commit_sha(self):self.bad(lambda e:e.update(commit_sha=''))
    def test_missing_plan_digest(self):self.bad(lambda e:e.update(plan_digest=''))
    def test_control_source_signed(self):self.bad(lambda e:e['controls'].update(source_signed=False))
    def test_control_runner_pinned(self):self.bad(lambda e:e['controls'].update(runner_pinned=False))
    def test_control_oidc_scoped(self):self.bad(lambda e:e['controls'].update(oidc_scoped=False))
    def test_control_least_privilege(self):self.bad(lambda e:e['controls'].update(least_privilege=False))
    def test_control_plan_fresh(self):self.bad(lambda e:e['controls'].update(plan_fresh=False))
    def test_control_policy_passed(self):self.bad(lambda e:e['controls'].update(policy_passed=False))
    def test_control_state_locked(self):self.bad(lambda e:e['controls'].update(state_locked=False))
    def test_control_backup_verified(self):self.bad(lambda e:e['controls'].update(backup_verified=False))
    def test_control_restore_tested(self):self.bad(lambda e:e['controls'].update(restore_tested=False))
    def test_control_dbre_approved(self):self.bad(lambda e:e['controls'].update(dbre_approved=False))
    def test_control_slo_healthy(self):self.bad(lambda e:e['controls'].update(slo_healthy=False))
    def test_control_audit_recorded(self):self.bad(lambda e:e['controls'].update(audit_recorded=False))
    def test_control_no_destructive_changes(self):self.bad(lambda e:e['controls'].update(no_destructive_changes=False))
if __name__=='__main__':unittest.main()
