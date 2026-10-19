import copy,json,unittest
from pathlib import Path
from test_gate import validate
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/safe.json').read_text())
POLICY=json.loads((ROOT/'policy.json').read_text())
class TestGateTests(unittest.TestCase):
    def bad(self,fn):
        e=copy.deepcopy(SAFE);fn(e);self.assertTrue(validate(e,POLICY))
    def test_safe(self):self.assertEqual(validate(SAFE,POLICY),[])
    def test_unsafe(self):self.assertTrue(validate(json.loads((ROOT/'fixtures/unsafe.json').read_text()),POLICY))
    def test_invalid_evidence(self):self.assertTrue(validate([],POLICY))
    def test_invalid_policy(self):self.assertTrue(validate(SAFE,[]))
    def test_policy_schema(self):
        p=copy.deepcopy(POLICY);p['schema_version']=2;self.assertTrue(validate(SAFE,p))
    def test_policy_target(self):
        p=copy.deepcopy(POLICY);p['target']={};self.assertTrue(validate(SAFE,p))
    def test_policy_controls(self):
        p=copy.deepcopy(POLICY);p['required_controls']=[];self.assertTrue(validate(SAFE,p))
    def test_policy_exact(self):
        p=copy.deepcopy(POLICY);p['require_exact_controls']=False;self.assertTrue(validate(SAFE,p))
    def test_schema(self):self.bad(lambda e:e.update(schema_version=2))
    def test_ticket(self):self.bad(lambda e:e.update(ticket='APPROVED'))
    def test_digest(self):self.bad(lambda e:e.update(artifact_digest='latest'))
    def test_missing_controls(self):self.bad(lambda e:e.pop('controls'))
    def test_extra_control(self):self.bad(lambda e:e['controls'].update(bypass=True))
    def test_target_environment(self):self.bad(lambda e:e.update(environment='production'))
    def test_target_repository(self):self.bad(lambda e:e.update(repository='production'))
    def test_target_cloud_account(self):self.bad(lambda e:e.update(cloud_account='production'))
    def test_target_kube_context(self):self.bad(lambda e:e.update(kube_context='production'))
    def test_target_source_commit(self):self.bad(lambda e:e.update(source_commit='production'))
    def test_target_policy_version(self):self.bad(lambda e:e.update(policy_version='production'))
    def test_control_source_signed(self):self.bad(lambda e:e['controls'].update(source_signed=False))
    def test_control_protected_branch(self):self.bad(lambda e:e['controls'].update(protected_branch=False))
    def test_control_toolchain_pinned(self):self.bad(lambda e:e['controls'].update(toolchain_pinned=False))
    def test_control_provider_lockfile_verified(self):self.bad(lambda e:e['controls'].update(provider_lockfile_verified=False))
    def test_control_format_passed(self):self.bad(lambda e:e['controls'].update(format_passed=False))
    def test_control_syntax_passed(self):self.bad(lambda e:e['controls'].update(syntax_passed=False))
    def test_control_static_scan_passed(self):self.bad(lambda e:e['controls'].update(static_scan_passed=False))
    def test_control_secrets_scan_passed(self):self.bad(lambda e:e['controls'].update(secrets_scan_passed=False))
    def test_control_unit_tests_passed(self):self.bad(lambda e:e['controls'].update(unit_tests_passed=False))
    def test_control_negative_tests_passed(self):self.bad(lambda e:e['controls'].update(negative_tests_passed=False))
    def test_control_policy_tests_passed(self):self.bad(lambda e:e['controls'].update(policy_tests_passed=False))
    def test_control_policy_enforced(self):self.bad(lambda e:e['controls'].update(policy_enforced=False))
    def test_control_plan_reviewed(self):self.bad(lambda e:e['controls'].update(plan_reviewed=False))
    def test_control_no_destructive_actions(self):self.bad(lambda e:e['controls'].update(no_destructive_actions=False))
    def test_control_target_verified(self):self.bad(lambda e:e['controls'].update(target_verified=False))
    def test_control_artifact_digest_verified(self):self.bad(lambda e:e['controls'].update(artifact_digest_verified=False))
    def test_control_identity_scoped(self):self.bad(lambda e:e['controls'].update(identity_scoped=False))
    def test_control_state_locked(self):self.bad(lambda e:e['controls'].update(state_locked=False))
    def test_control_state_encrypted(self):self.bad(lambda e:e['controls'].update(state_encrypted=False))
    def test_control_integration_tests_passed(self):self.bad(lambda e:e['controls'].update(integration_tests_passed=False))
    def test_control_ephemeral_isolation(self):self.bad(lambda e:e['controls'].update(ephemeral_isolation=False))
    def test_control_cleanup_verified(self):self.bad(lambda e:e['controls'].update(cleanup_verified=False))
    def test_control_kubernetes_rbac_tested(self):self.bad(lambda e:e['controls'].update(kubernetes_rbac_tested=False))
    def test_control_admission_tested(self):self.bad(lambda e:e['controls'].update(admission_tested=False))
    def test_control_gitops_reconciliation_tested(self):self.bad(lambda e:e['controls'].update(gitops_reconciliation_tested=False))
    def test_control_dbre_approved(self):self.bad(lambda e:e['controls'].update(dbre_approved=False))
    def test_control_backup_verified(self):self.bad(lambda e:e['controls'].update(backup_verified=False))
    def test_control_restore_rehearsed(self):self.bad(lambda e:e['controls'].update(restore_rehearsed=False))
    def test_control_slo_healthy(self):self.bad(lambda e:e['controls'].update(slo_healthy=False))
    def test_control_audit_retained(self):self.bad(lambda e:e['controls'].update(audit_retained=False))
    def test_unit_tests(self):self.bad(lambda e:e.update(unit_tests=0))
    def test_negative_tests(self):self.bad(lambda e:e.update(negative_tests=0))
    def test_skipped_critical(self):self.bad(lambda e:e.update(skipped_critical=1))
    def test_destroy_count(self):self.bad(lambda e:e.update(destroy_count=1))
    def test_replace_count(self):self.bad(lambda e:e.update(replace_count=1))
    def test_measured_rpo_minutes(self):self.bad(lambda e:e.update(measured_rpo_minutes=1000))
    def test_measured_rto_minutes(self):self.bad(lambda e:e.update(measured_rto_minutes=1000))
    def test_policy_min_unit_tests(self):
        p=copy.deepcopy(POLICY);p['min_unit_tests']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_min_negative_tests(self):
        p=copy.deepcopy(POLICY);p['min_negative_tests']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_skipped_critical(self):
        p=copy.deepcopy(POLICY);p['max_skipped_critical']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_destroy(self):
        p=copy.deepcopy(POLICY);p['max_destroy']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_replace(self):
        p=copy.deepcopy(POLICY);p['max_replace']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_rpo_minutes(self):
        p=copy.deepcopy(POLICY);p['max_rpo_minutes']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_rto_minutes(self):
        p=copy.deepcopy(POLICY);p['max_rto_minutes']=999;self.assertTrue(validate(SAFE,p))
if __name__=="__main__":unittest.main()
