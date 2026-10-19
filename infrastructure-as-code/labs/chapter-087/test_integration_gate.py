import copy,json,unittest
from pathlib import Path
from integration_gate import validate
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/safe.json').read_text())
POLICY=json.loads((ROOT/'policy.json').read_text())
class IntegrationGateTests(unittest.TestCase):
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
    def test_target_cloud_account(self):self.bad(lambda e:e.update(cloud_account='production'))
    def test_target_kube_context(self):self.bad(lambda e:e.update(kube_context='production'))
    def test_target_repository(self):self.bad(lambda e:e.update(repository='production'))
    def test_target_region(self):self.bad(lambda e:e.update(region='production'))
    def test_target_run_id(self):self.bad(lambda e:e.update(run_id='production'))
    def test_target_owner(self):self.bad(lambda e:e.update(owner='production'))
    def test_control_source_signed(self):self.bad(lambda e:e['controls'].update(source_signed=False))
    def test_control_protected_branch(self):self.bad(lambda e:e['controls'].update(protected_branch=False))
    def test_control_test_only_oidc(self):self.bad(lambda e:e['controls'].update(test_only_oidc=False))
    def test_control_exact_cloud_target(self):self.bad(lambda e:e['controls'].update(exact_cloud_target=False))
    def test_control_unique_run_id(self):self.bad(lambda e:e['controls'].update(unique_run_id=False))
    def test_control_owner_assigned(self):self.bad(lambda e:e['controls'].update(owner_assigned=False))
    def test_control_lease_active(self):self.bad(lambda e:e['controls'].update(lease_active=False))
    def test_control_ttl_bounded(self):self.bad(lambda e:e['controls'].update(ttl_bounded=False))
    def test_control_cost_budget_set(self):self.bad(lambda e:e['controls'].update(cost_budget_set=False))
    def test_control_resources_tagged(self):self.bad(lambda e:e['controls'].update(resources_tagged=False))
    def test_control_state_isolated(self):self.bad(lambda e:e['controls'].update(state_isolated=False))
    def test_control_state_encrypted(self):self.bad(lambda e:e['controls'].update(state_encrypted=False))
    def test_control_terraform_plan_reviewed(self):self.bad(lambda e:e['controls'].update(terraform_plan_reviewed=False))
    def test_control_terratest_passed(self):self.bad(lambda e:e['controls'].update(terratest_passed=False))
    def test_control_molecule_converge_passed(self):self.bad(lambda e:e['controls'].update(molecule_converge_passed=False))
    def test_control_molecule_idempotence_passed(self):self.bad(lambda e:e['controls'].update(molecule_idempotence_passed=False))
    def test_control_native_resource_assertions(self):self.bad(lambda e:e['controls'].update(native_resource_assertions=False))
    def test_control_negative_tests_passed(self):self.bad(lambda e:e['controls'].update(negative_tests_passed=False))
    def test_control_kubernetes_admission_tested(self):self.bad(lambda e:e['controls'].update(kubernetes_admission_tested=False))
    def test_control_kubernetes_rbac_tested(self):self.bad(lambda e:e['controls'].update(kubernetes_rbac_tested=False))
    def test_control_gitops_reconciliation_tested(self):self.bad(lambda e:e['controls'].update(gitops_reconciliation_tested=False))
    def test_control_database_isolated(self):self.bad(lambda e:e['controls'].update(database_isolated=False))
    def test_control_backup_verified(self):self.bad(lambda e:e['controls'].update(backup_verified=False))
    def test_control_restore_rehearsed(self):self.bad(lambda e:e['controls'].update(restore_rehearsed=False))
    def test_control_kms_access_verified(self):self.bad(lambda e:e['controls'].update(kms_access_verified=False))
    def test_control_rpo_accepted(self):self.bad(lambda e:e['controls'].update(rpo_accepted=False))
    def test_control_rto_accepted(self):self.bad(lambda e:e['controls'].update(rto_accepted=False))
    def test_control_slo_healthy(self):self.bad(lambda e:e['controls'].update(slo_healthy=False))
    def test_control_cleanup_executed(self):self.bad(lambda e:e['controls'].update(cleanup_executed=False))
    def test_control_cleanup_inventory_zero(self):self.bad(lambda e:e['controls'].update(cleanup_inventory_zero=False))
    def test_control_credentials_revoked(self):self.bad(lambda e:e['controls'].update(credentials_revoked=False))
    def test_control_audit_retained(self):self.bad(lambda e:e['controls'].update(audit_retained=False))
    def test_native_assertions(self):self.bad(lambda e:e.update(native_assertions=0))
    def test_negative_tests(self):self.bad(lambda e:e.update(negative_tests=0))
    def test_skipped_critical(self):self.bad(lambda e:e.update(skipped_critical=1))
    def test_orphaned_resources(self):self.bad(lambda e:e.update(orphaned_resources=1))
    def test_cost_usd(self):self.bad(lambda e:e.update(cost_usd=1000))
    def test_lease_minutes(self):self.bad(lambda e:e.update(lease_minutes=1000))
    def test_rpo_minutes(self):self.bad(lambda e:e.update(rpo_minutes=1000))
    def test_rto_minutes(self):self.bad(lambda e:e.update(rto_minutes=1000))
    def test_policy_min_native_assertions(self):
        p=copy.deepcopy(POLICY);p['min_native_assertions']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_min_negative_tests(self):
        p=copy.deepcopy(POLICY);p['min_negative_tests']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_skipped_critical(self):
        p=copy.deepcopy(POLICY);p['max_skipped_critical']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_orphaned_resources(self):
        p=copy.deepcopy(POLICY);p['max_orphaned_resources']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_cost_usd(self):
        p=copy.deepcopy(POLICY);p['max_cost_usd']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_lease_minutes(self):
        p=copy.deepcopy(POLICY);p['max_lease_minutes']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_rpo_minutes(self):
        p=copy.deepcopy(POLICY);p['max_rpo_minutes']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_rto_minutes(self):
        p=copy.deepcopy(POLICY);p['max_rto_minutes']=999;self.assertTrue(validate(SAFE,p))
if __name__=="__main__":unittest.main()
