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
    def test_target_cloud_account(self):self.bad(lambda e:e.update(cloud_account='production'))
    def test_target_kube_context(self):self.bad(lambda e:e.update(kube_context='production'))
    def test_target_repository(self):self.bad(lambda e:e.update(repository='production'))
    def test_target_source_commit(self):self.bad(lambda e:e.update(source_commit='production'))
    def test_target_owner(self):self.bad(lambda e:e.update(owner='production'))
    def test_control_source_approved(self):self.bad(lambda e:e['controls'].update(source_approved=False))
    def test_control_protected_branch(self):self.bad(lambda e:e['controls'].update(protected_branch=False))
    def test_control_immutable_artifact(self):self.bad(lambda e:e['controls'].update(immutable_artifact=False))
    def test_control_exact_target(self):self.bad(lambda e:e['controls'].update(exact_target=False))
    def test_control_read_only_scanner(self):self.bad(lambda e:e['controls'].update(read_only_scanner=False))
    def test_control_inventory_complete(self):self.bad(lambda e:e['controls'].update(inventory_complete=False))
    def test_control_inventory_fresh(self):self.bad(lambda e:e['controls'].update(inventory_fresh=False))
    def test_control_state_version_preserved(self):self.bad(lambda e:e['controls'].update(state_version_preserved=False))
    def test_control_terraform_refresh_reviewed(self):self.bad(lambda e:e['controls'].update(terraform_refresh_reviewed=False))
    def test_control_opentofu_refresh_reviewed(self):self.bad(lambda e:e['controls'].update(opentofu_refresh_reviewed=False))
    def test_control_pulumi_preview_reviewed(self):self.bad(lambda e:e['controls'].update(pulumi_preview_reviewed=False))
    def test_control_cloudformation_drift_reviewed(self):self.bad(lambda e:e['controls'].update(cloudformation_drift_reviewed=False))
    def test_control_bicep_whatif_reviewed(self):self.bad(lambda e:e['controls'].update(bicep_whatif_reviewed=False))
    def test_control_aws_config_checked(self):self.bad(lambda e:e['controls'].update(aws_config_checked=False))
    def test_control_azure_resource_graph_checked(self):self.bad(lambda e:e['controls'].update(azure_resource_graph_checked=False))
    def test_control_gcp_asset_inventory_checked(self):self.bad(lambda e:e['controls'].update(gcp_asset_inventory_checked=False))
    def test_control_kubernetes_diff_reviewed(self):self.bad(lambda e:e['controls'].update(kubernetes_diff_reviewed=False))
    def test_control_gitops_revision_verified(self):self.bad(lambda e:e['controls'].update(gitops_revision_verified=False))
    def test_control_opa_policy_enforced(self):self.bad(lambda e:e['controls'].update(opa_policy_enforced=False))
    def test_control_sentinel_policy_enforced(self):self.bad(lambda e:e['controls'].update(sentinel_policy_enforced=False))
    def test_control_change_ticket_verified(self):self.bad(lambda e:e['controls'].update(change_ticket_verified=False))
    def test_control_actor_identity_verified(self):self.bad(lambda e:e['controls'].update(actor_identity_verified=False))
    def test_control_exception_independently_approved(self):self.bad(lambda e:e['controls'].update(exception_independently_approved=False))
    def test_control_no_auto_destroy(self):self.bad(lambda e:e['controls'].update(no_auto_destroy=False))
    def test_control_remediation_requires_review(self):self.bad(lambda e:e['controls'].update(remediation_requires_review=False))
    def test_control_audit_logs_enabled(self):self.bad(lambda e:e['controls'].update(audit_logs_enabled=False))
    def test_control_evidence_integrity_verified(self):self.bad(lambda e:e['controls'].update(evidence_integrity_verified=False))
    def test_control_dbre_backup_verified(self):self.bad(lambda e:e['controls'].update(dbre_backup_verified=False))
    def test_control_dbre_restore_rehearsed(self):self.bad(lambda e:e['controls'].update(dbre_restore_rehearsed=False))
    def test_control_rpo_accepted(self):self.bad(lambda e:e['controls'].update(rpo_accepted=False))
    def test_control_rto_accepted(self):self.bad(lambda e:e['controls'].update(rto_accepted=False))
    def test_control_slo_healthy(self):self.bad(lambda e:e['controls'].update(slo_healthy=False))
    def test_critical_findings(self):self.bad(lambda e:e.update(critical_findings=1000))
    def test_destructive_actions(self):self.bad(lambda e:e.update(destructive_actions=1000))
    def test_missing_evidence(self):self.bad(lambda e:e.update(missing_evidence=1000))
    def test_snapshot_age_minutes(self):self.bad(lambda e:e.update(snapshot_age_minutes=1000))
    def test_detection_latency_minutes(self):self.bad(lambda e:e.update(detection_latency_minutes=1000))
    def test_rpo_minutes(self):self.bad(lambda e:e.update(rpo_minutes=1000))
    def test_rto_minutes(self):self.bad(lambda e:e.update(rto_minutes=1000))
    def test_coverage_low(self):self.bad(lambda e:e.update(inventory_coverage_percent=50))
    def test_coverage_high(self):self.bad(lambda e:e.update(inventory_coverage_percent=101))
    def test_coverage_bool(self):self.bad(lambda e:e.update(inventory_coverage_percent=True))
    def test_policy_max_critical_findings(self):
        p=copy.deepcopy(POLICY);p['max_critical_findings']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_destructive_actions(self):
        p=copy.deepcopy(POLICY);p['max_destructive_actions']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_missing_evidence(self):
        p=copy.deepcopy(POLICY);p['max_missing_evidence']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_snapshot_age_minutes(self):
        p=copy.deepcopy(POLICY);p['max_snapshot_age_minutes']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_min_inventory_coverage_percent(self):
        p=copy.deepcopy(POLICY);p['min_inventory_coverage_percent']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_detection_latency_minutes(self):
        p=copy.deepcopy(POLICY);p['max_detection_latency_minutes']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_rpo_minutes(self):
        p=copy.deepcopy(POLICY);p['max_rpo_minutes']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_rto_minutes(self):
        p=copy.deepcopy(POLICY);p['max_rto_minutes']=999;self.assertTrue(validate(SAFE,p))
if __name__=="__main__":unittest.main()
