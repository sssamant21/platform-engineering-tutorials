import copy,json,unittest
from pathlib import Path
from capstone_gate import validate
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/safe.json').read_text())
POLICY=json.loads((ROOT/'policy.json').read_text())
class CapstoneGateTests(unittest.TestCase):
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
    def test_target_source_commit(self):self.bad(lambda e:e.update(source_commit='production'))
    def test_target_run_id(self):self.bad(lambda e:e.update(run_id='production'))
    def test_target_owner(self):self.bad(lambda e:e.update(owner='production'))
    def test_control_source_approved(self):self.bad(lambda e:e['controls'].update(source_approved=False))
    def test_control_protected_branch(self):self.bad(lambda e:e['controls'].update(protected_branch=False))
    def test_control_immutable_artifact(self):self.bad(lambda e:e['controls'].update(immutable_artifact=False))
    def test_control_exact_target(self):self.bad(lambda e:e['controls'].update(exact_target=False))
    def test_control_oidc_scoped(self):self.bad(lambda e:e['controls'].update(oidc_scoped=False))
    def test_control_state_encrypted(self):self.bad(lambda e:e['controls'].update(state_encrypted=False))
    def test_control_state_isolated(self):self.bad(lambda e:e['controls'].update(state_isolated=False))
    def test_control_secrets_scanned(self):self.bad(lambda e:e['controls'].update(secrets_scanned=False))
    def test_control_sbom_verified(self):self.bad(lambda e:e['controls'].update(sbom_verified=False))
    def test_control_provenance_verified(self):self.bad(lambda e:e['controls'].update(provenance_verified=False))
    def test_control_terraform_validated(self):self.bad(lambda e:e['controls'].update(terraform_validated=False))
    def test_control_opentofu_validated(self):self.bad(lambda e:e['controls'].update(opentofu_validated=False))
    def test_control_terratest_passed(self):self.bad(lambda e:e['controls'].update(terratest_passed=False))
    def test_control_molecule_converge_passed(self):self.bad(lambda e:e['controls'].update(molecule_converge_passed=False))
    def test_control_molecule_idempotence_passed(self):self.bad(lambda e:e['controls'].update(molecule_idempotence_passed=False))
    def test_control_pulumi_preview_reviewed(self):self.bad(lambda e:e['controls'].update(pulumi_preview_reviewed=False))
    def test_control_cloudformation_changeset_reviewed(self):self.bad(lambda e:e['controls'].update(cloudformation_changeset_reviewed=False))
    def test_control_bicep_whatif_reviewed(self):self.bad(lambda e:e['controls'].update(bicep_whatif_reviewed=False))
    def test_control_opa_enforced(self):self.bad(lambda e:e['controls'].update(opa_enforced=False))
    def test_control_sentinel_enforced(self):self.bad(lambda e:e['controls'].update(sentinel_enforced=False))
    def test_control_negative_tests_passed(self):self.bad(lambda e:e['controls'].update(negative_tests_passed=False))
    def test_control_aws_policy_checked(self):self.bad(lambda e:e['controls'].update(aws_policy_checked=False))
    def test_control_azure_policy_checked(self):self.bad(lambda e:e['controls'].update(azure_policy_checked=False))
    def test_control_gcp_policy_checked(self):self.bad(lambda e:e['controls'].update(gcp_policy_checked=False))
    def test_control_kubernetes_admission_enforced(self):self.bad(lambda e:e['controls'].update(kubernetes_admission_enforced=False))
    def test_control_kubernetes_rbac_checked(self):self.bad(lambda e:e['controls'].update(kubernetes_rbac_checked=False))
    def test_control_gitops_revision_verified(self):self.bad(lambda e:e['controls'].update(gitops_revision_verified=False))
    def test_control_drift_observation_fresh(self):self.bad(lambda e:e['controls'].update(drift_observation_fresh=False))
    def test_control_drift_remediation_approved(self):self.bad(lambda e:e['controls'].update(drift_remediation_approved=False))
    def test_control_no_auto_destroy(self):self.bad(lambda e:e['controls'].update(no_auto_destroy=False))
    def test_control_exception_independently_approved(self):self.bad(lambda e:e['controls'].update(exception_independently_approved=False))
    def test_control_audit_logs_enabled(self):self.bad(lambda e:e['controls'].update(audit_logs_enabled=False))
    def test_control_evidence_chain_verified(self):self.bad(lambda e:e['controls'].update(evidence_chain_verified=False))
    def test_control_retention_verified(self):self.bad(lambda e:e['controls'].update(retention_verified=False))
    def test_control_backup_encrypted(self):self.bad(lambda e:e['controls'].update(backup_encrypted=False))
    def test_control_restore_rehearsed(self):self.bad(lambda e:e['controls'].update(restore_rehearsed=False))
    def test_control_kms_decrypt_verified(self):self.bad(lambda e:e['controls'].update(kms_decrypt_verified=False))
    def test_control_rpo_accepted(self):self.bad(lambda e:e['controls'].update(rpo_accepted=False))
    def test_control_rto_accepted(self):self.bad(lambda e:e['controls'].update(rto_accepted=False))
    def test_control_slo_healthy(self):self.bad(lambda e:e['controls'].update(slo_healthy=False))
    def test_min_native_assertions(self):self.bad(lambda e:e.update(native_assertions=0))
    def test_min_negative_tests(self):self.bad(lambda e:e.update(negative_tests=0))
    def test_max_skipped_critical(self):self.bad(lambda e:e.update(skipped_critical=1000))
    def test_max_critical_findings(self):self.bad(lambda e:e.update(critical_findings=1000))
    def test_max_orphaned_resources(self):self.bad(lambda e:e.update(orphaned_resources=1000))
    def test_max_evidence_age_hours(self):self.bad(lambda e:e.update(evidence_age_hours=1000))
    def test_max_cost_usd(self):self.bad(lambda e:e.update(cost_usd=1000))
    def test_max_lease_minutes(self):self.bad(lambda e:e.update(lease_minutes=1000))
    def test_max_rpo_minutes(self):self.bad(lambda e:e.update(rpo_minutes=1000))
    def test_max_rto_minutes(self):self.bad(lambda e:e.update(rto_minutes=1000))
    def test_policy_min_native_assertions(self):
        p=copy.deepcopy(POLICY);p['min_native_assertions']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_min_negative_tests(self):
        p=copy.deepcopy(POLICY);p['min_negative_tests']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_skipped_critical(self):
        p=copy.deepcopy(POLICY);p['max_skipped_critical']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_critical_findings(self):
        p=copy.deepcopy(POLICY);p['max_critical_findings']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_orphaned_resources(self):
        p=copy.deepcopy(POLICY);p['max_orphaned_resources']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_evidence_age_hours(self):
        p=copy.deepcopy(POLICY);p['max_evidence_age_hours']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_cost_usd(self):
        p=copy.deepcopy(POLICY);p['max_cost_usd']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_lease_minutes(self):
        p=copy.deepcopy(POLICY);p['max_lease_minutes']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_rpo_minutes(self):
        p=copy.deepcopy(POLICY);p['max_rpo_minutes']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_rto_minutes(self):
        p=copy.deepcopy(POLICY);p['max_rto_minutes']=999;self.assertTrue(validate(SAFE,p))
if __name__=="__main__":unittest.main()
