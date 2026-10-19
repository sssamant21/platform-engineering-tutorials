import copy,json,unittest
from pathlib import Path
from drift_gate import validate
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/safe.json').read_text())
POLICY=json.loads((ROOT/'policy.json').read_text())
class DriftGateTests(unittest.TestCase):
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
    def test_control_source_approved(self):self.bad(lambda e:e['controls'].update(source_approved=False))
    def test_control_protected_branch(self):self.bad(lambda e:e['controls'].update(protected_branch=False))
    def test_control_artifact_digest_verified(self):self.bad(lambda e:e['controls'].update(artifact_digest_verified=False))
    def test_control_exact_cloud_target(self):self.bad(lambda e:e['controls'].update(exact_cloud_target=False))
    def test_control_least_privilege_readonly(self):self.bad(lambda e:e['controls'].update(least_privilege_readonly=False))
    def test_control_observation_fresh(self):self.bad(lambda e:e['controls'].update(observation_fresh=False))
    def test_control_inventory_complete(self):self.bad(lambda e:e['controls'].update(inventory_complete=False))
    def test_control_terraform_refresh_reviewed(self):self.bad(lambda e:e['controls'].update(terraform_refresh_reviewed=False))
    def test_control_opentofu_plan_reviewed(self):self.bad(lambda e:e['controls'].update(opentofu_plan_reviewed=False))
    def test_control_pulumi_drift_checked(self):self.bad(lambda e:e['controls'].update(pulumi_drift_checked=False))
    def test_control_cloudformation_drift_checked(self):self.bad(lambda e:e['controls'].update(cloudformation_drift_checked=False))
    def test_control_bicep_whatif_checked(self):self.bad(lambda e:e['controls'].update(bicep_whatif_checked=False))
    def test_control_aws_config_enabled(self):self.bad(lambda e:e['controls'].update(aws_config_enabled=False))
    def test_control_azure_policy_enabled(self):self.bad(lambda e:e['controls'].update(azure_policy_enabled=False))
    def test_control_gcp_org_policy_enabled(self):self.bad(lambda e:e['controls'].update(gcp_org_policy_enabled=False))
    def test_control_kubernetes_admission_enforced(self):self.bad(lambda e:e['controls'].update(kubernetes_admission_enforced=False))
    def test_control_gitops_revision_verified(self):self.bad(lambda e:e['controls'].update(gitops_revision_verified=False))
    def test_control_opa_enforced(self):self.bad(lambda e:e['controls'].update(opa_enforced=False))
    def test_control_sentinel_enforced(self):self.bad(lambda e:e['controls'].update(sentinel_enforced=False))
    def test_control_audit_logs_enabled(self):self.bad(lambda e:e['controls'].update(audit_logs_enabled=False))
    def test_control_evidence_hash_verified(self):self.bad(lambda e:e['controls'].update(evidence_hash_verified=False))
    def test_control_exceptions_unexpired(self):self.bad(lambda e:e['controls'].update(exceptions_unexpired=False))
    def test_control_exception_approver_independent(self):self.bad(lambda e:e['controls'].update(exception_approver_independent=False))
    def test_control_no_auto_destroy(self):self.bad(lambda e:e['controls'].update(no_auto_destroy=False))
    def test_control_dbre_approved(self):self.bad(lambda e:e['controls'].update(dbre_approved=False))
    def test_control_backup_verified(self):self.bad(lambda e:e['controls'].update(backup_verified=False))
    def test_control_restore_rehearsed(self):self.bad(lambda e:e['controls'].update(restore_rehearsed=False))
    def test_control_rpo_accepted(self):self.bad(lambda e:e['controls'].update(rpo_accepted=False))
    def test_control_rto_accepted(self):self.bad(lambda e:e['controls'].update(rto_accepted=False))
    def test_control_slo_healthy(self):self.bad(lambda e:e['controls'].update(slo_healthy=False))
    def test_critical_findings(self):self.bad(lambda e:e.update(critical_findings=1000))
    def test_observation_age_minutes(self):self.bad(lambda e:e.update(observation_age_minutes=1000))
    def test_exception_age_days(self):self.bad(lambda e:e.update(exception_age_days=1000))
    def test_rpo_minutes(self):self.bad(lambda e:e.update(rpo_minutes=1000))
    def test_rto_minutes(self):self.bad(lambda e:e.update(rto_minutes=1000))
    def test_policy_max_critical_findings(self):
        p=copy.deepcopy(POLICY);p['max_critical_findings']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_observation_age_minutes(self):
        p=copy.deepcopy(POLICY);p['max_observation_age_minutes']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_exception_age_days(self):
        p=copy.deepcopy(POLICY);p['max_exception_age_days']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_rpo_minutes(self):
        p=copy.deepcopy(POLICY);p['max_rpo_minutes']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_rto_minutes(self):
        p=copy.deepcopy(POLICY);p['max_rto_minutes']=999;self.assertTrue(validate(SAFE,p))
if __name__=="__main__":unittest.main()
