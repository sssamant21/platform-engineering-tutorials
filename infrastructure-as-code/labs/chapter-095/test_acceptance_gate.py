import copy,json,unittest
from pathlib import Path
from acceptance_gate import validate
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/safe.json').read_text())
POLICY=json.loads((ROOT/'policy.json').read_text())
class AcceptanceGateTests(unittest.TestCase):
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
    def test_control_immutable_plan(self):self.bad(lambda e:e['controls'].update(immutable_plan=False))
    def test_control_target_verified(self):self.bad(lambda e:e['controls'].update(target_verified=False))
    def test_control_state_version_preserved(self):self.bad(lambda e:e['controls'].update(state_version_preserved=False))
    def test_control_read_only_inventory(self):self.bad(lambda e:e['controls'].update(read_only_inventory=False))
    def test_control_inventory_complete(self):self.bad(lambda e:e['controls'].update(inventory_complete=False))
    def test_control_inventory_fresh(self):self.bad(lambda e:e['controls'].update(inventory_fresh=False))
    def test_control_aws_audit_healthy(self):self.bad(lambda e:e['controls'].update(aws_audit_healthy=False))
    def test_control_azure_audit_healthy(self):self.bad(lambda e:e['controls'].update(azure_audit_healthy=False))
    def test_control_gcp_audit_healthy(self):self.bad(lambda e:e['controls'].update(gcp_audit_healthy=False))
    def test_control_otel_collector_healthy(self):self.bad(lambda e:e['controls'].update(otel_collector_healthy=False))
    def test_control_prometheus_scrape_fresh(self):self.bad(lambda e:e['controls'].update(prometheus_scrape_fresh=False))
    def test_control_metrics_cardinality_bounded(self):self.bad(lambda e:e['controls'].update(metrics_cardinality_bounded=False))
    def test_control_logs_redacted(self):self.bad(lambda e:e['controls'].update(logs_redacted=False))
    def test_control_traces_redacted(self):self.bad(lambda e:e['controls'].update(traces_redacted=False))
    def test_control_gitops_revision_verified(self):self.bad(lambda e:e['controls'].update(gitops_revision_verified=False))
    def test_control_drift_three_way_reviewed(self):self.bad(lambda e:e['controls'].update(drift_three_way_reviewed=False))
    def test_control_change_ticket_verified(self):self.bad(lambda e:e['controls'].update(change_ticket_verified=False))
    def test_control_incident_timeline_utc(self):self.bad(lambda e:e['controls'].update(incident_timeline_utc=False))
    def test_control_alternative_causes_reviewed(self):self.bad(lambda e:e['controls'].update(alternative_causes_reviewed=False))
    def test_control_sli_denominator_valid(self):self.bad(lambda e:e['controls'].update(sli_denominator_valid=False))
    def test_control_error_budget_verified(self):self.bad(lambda e:e['controls'].update(error_budget_verified=False))
    def test_control_multi_window_alerts_verified(self):self.bad(lambda e:e['controls'].update(multi_window_alerts_verified=False))
    def test_control_paging_delivery_verified(self):self.bad(lambda e:e['controls'].update(paging_delivery_verified=False))
    def test_control_incident_commander_assigned(self):self.bad(lambda e:e['controls'].update(incident_commander_assigned=False))
    def test_control_no_auto_destroy(self):self.bad(lambda e:e['controls'].update(no_auto_destroy=False))
    def test_control_rollback_approved(self):self.bad(lambda e:e['controls'].update(rollback_approved=False))
    def test_control_dbre_backup_verified(self):self.bad(lambda e:e['controls'].update(dbre_backup_verified=False))
    def test_control_dbre_restore_rehearsed(self):self.bad(lambda e:e['controls'].update(dbre_restore_rehearsed=False))
    def test_control_rpo_accepted(self):self.bad(lambda e:e['controls'].update(rpo_accepted=False))
    def test_control_rto_accepted(self):self.bad(lambda e:e['controls'].update(rto_accepted=False))
    def test_control_application_slo_healthy(self):self.bad(lambda e:e['controls'].update(application_slo_healthy=False))
    def test_control_data_integrity_verified(self):self.bad(lambda e:e['controls'].update(data_integrity_verified=False))
    def test_control_audit_evidence_retained(self):self.bad(lambda e:e['controls'].update(audit_evidence_retained=False))
    def test_control_cleanup_zero_orphans(self):self.bad(lambda e:e['controls'].update(cleanup_zero_orphans=False))
    def test_critical_findings(self):self.bad(lambda e:e.update(critical_findings=1000))
    def test_destructive_actions(self):self.bad(lambda e:e.update(destructive_actions=1000))
    def test_missing_evidence(self):self.bad(lambda e:e.update(missing_evidence=1000))
    def test_inventory_age_minutes(self):self.bad(lambda e:e.update(inventory_age_minutes=1000))
    def test_telemetry_age_minutes(self):self.bad(lambda e:e.update(telemetry_age_minutes=1000))
    def test_error_budget_consumed_percent(self):self.bad(lambda e:e.update(error_budget_consumed_percent=1000))
    def test_rpo_minutes(self):self.bad(lambda e:e.update(rpo_minutes=1000))
    def test_rto_minutes(self):self.bad(lambda e:e.update(rto_minutes=1000))
    def test_orphan_resources(self):self.bad(lambda e:e.update(orphan_resources=1000))
    def test_policy_max_critical_findings(self):
        p=copy.deepcopy(POLICY);p['max_critical_findings']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_destructive_actions(self):
        p=copy.deepcopy(POLICY);p['max_destructive_actions']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_missing_evidence(self):
        p=copy.deepcopy(POLICY);p['max_missing_evidence']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_inventory_age_minutes(self):
        p=copy.deepcopy(POLICY);p['max_inventory_age_minutes']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_telemetry_age_minutes(self):
        p=copy.deepcopy(POLICY);p['max_telemetry_age_minutes']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_error_budget_consumed_percent(self):
        p=copy.deepcopy(POLICY);p['max_error_budget_consumed_percent']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_rpo_minutes(self):
        p=copy.deepcopy(POLICY);p['max_rpo_minutes']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_rto_minutes(self):
        p=copy.deepcopy(POLICY);p['max_rto_minutes']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_orphan_resources(self):
        p=copy.deepcopy(POLICY);p['max_orphan_resources']=999;self.assertTrue(validate(SAFE,p))
if __name__=="__main__":unittest.main()
