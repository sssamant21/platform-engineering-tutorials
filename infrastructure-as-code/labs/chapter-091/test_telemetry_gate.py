import copy,json,unittest
from pathlib import Path
from telemetry_gate import validate
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/safe.json').read_text())
POLICY=json.loads((ROOT/'policy.json').read_text())
class TelemetryGateTests(unittest.TestCase):
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
    def test_policy_metrics(self):
        p=copy.deepcopy(POLICY);p['required_metrics']=[];self.assertTrue(validate(SAFE,p))
    def test_policy_exact(self):
        p=copy.deepcopy(POLICY);p['require_exact_controls']=False;self.assertTrue(validate(SAFE,p))
    def test_schema(self):self.bad(lambda e:e.update(schema_version=2))
    def test_ticket(self):self.bad(lambda e:e.update(ticket='APPROVED'))
    def test_digest(self):self.bad(lambda e:e.update(artifact_digest='latest'))
    def test_missing_controls(self):self.bad(lambda e:e.pop('controls'))
    def test_extra_control(self):self.bad(lambda e:e['controls'].update(bypass=True))
    def test_metrics(self):self.bad(lambda e:e.update(metrics=[]))
    def test_target_environment(self):self.bad(lambda e:e.update(environment='production'))
    def test_target_cloud_account(self):self.bad(lambda e:e.update(cloud_account='production'))
    def test_target_kube_context(self):self.bad(lambda e:e.update(kube_context='production'))
    def test_target_repository(self):self.bad(lambda e:e.update(repository='production'))
    def test_target_source_commit(self):self.bad(lambda e:e.update(source_commit='production'))
    def test_target_owner(self):self.bad(lambda e:e.update(owner='production'))
    def test_control_source_approved(self):self.bad(lambda e:e['controls'].update(source_approved=False))
    def test_control_target_verified(self):self.bad(lambda e:e['controls'].update(target_verified=False))
    def test_control_otel_collector_healthy(self):self.bad(lambda e:e['controls'].update(otel_collector_healthy=False))
    def test_control_prometheus_scrape_healthy(self):self.bad(lambda e:e['controls'].update(prometheus_scrape_healthy=False))
    def test_control_logs_redacted(self):self.bad(lambda e:e['controls'].update(logs_redacted=False))
    def test_control_traces_redacted(self):self.bad(lambda e:e['controls'].update(traces_redacted=False))
    def test_control_audit_logs_enabled(self):self.bad(lambda e:e['controls'].update(audit_logs_enabled=False))
    def test_control_collector_tls_enforced(self):self.bad(lambda e:e['controls'].update(collector_tls_enforced=False))
    def test_control_exporter_authenticated(self):self.bad(lambda e:e['controls'].update(exporter_authenticated=False))
    def test_control_metrics_cardinality_bounded(self):self.bad(lambda e:e['controls'].update(metrics_cardinality_bounded=False))
    def test_control_metrics_fresh(self):self.bad(lambda e:e['controls'].update(metrics_fresh=False))
    def test_control_logs_fresh(self):self.bad(lambda e:e['controls'].update(logs_fresh=False))
    def test_control_traces_fresh(self):self.bad(lambda e:e['controls'].update(traces_fresh=False))
    def test_control_alert_routes_verified(self):self.bad(lambda e:e['controls'].update(alert_routes_verified=False))
    def test_control_runbooks_linked(self):self.bad(lambda e:e['controls'].update(runbooks_linked=False))
    def test_control_slo_calculated(self):self.bad(lambda e:e['controls'].update(slo_calculated=False))
    def test_control_burn_rate_reviewed(self):self.bad(lambda e:e['controls'].update(burn_rate_reviewed=False))
    def test_control_error_budget_reviewed(self):self.bad(lambda e:e['controls'].update(error_budget_reviewed=False))
    def test_control_gitops_observed(self):self.bad(lambda e:e['controls'].update(gitops_observed=False))
    def test_control_drift_observed(self):self.bad(lambda e:e['controls'].update(drift_observed=False))
    def test_control_policy_decisions_observed(self):self.bad(lambda e:e['controls'].update(policy_decisions_observed=False))
    def test_control_state_lock_observed(self):self.bad(lambda e:e['controls'].update(state_lock_observed=False))
    def test_control_provider_throttling_observed(self):self.bad(lambda e:e['controls'].update(provider_throttling_observed=False))
    def test_control_dbre_replication_observed(self):self.bad(lambda e:e['controls'].update(dbre_replication_observed=False))
    def test_control_dbre_backup_observed(self):self.bad(lambda e:e['controls'].update(dbre_backup_observed=False))
    def test_control_dbre_restore_rehearsed(self):self.bad(lambda e:e['controls'].update(dbre_restore_rehearsed=False))
    def test_control_rpo_accepted(self):self.bad(lambda e:e['controls'].update(rpo_accepted=False))
    def test_control_rto_accepted(self):self.bad(lambda e:e['controls'].update(rto_accepted=False))
    def test_control_slo_healthy(self):self.bad(lambda e:e['controls'].update(slo_healthy=False))
    def test_control_retention_verified(self):self.bad(lambda e:e['controls'].update(retention_verified=False))
    def test_critical_findings(self):self.bad(lambda e:e.update(critical_findings=1000))
    def test_telemetry_age_minutes(self):self.bad(lambda e:e.update(telemetry_age_minutes=1000))
    def test_drift_age_minutes(self):self.bad(lambda e:e.update(drift_age_minutes=1000))
    def test_export_failures(self):self.bad(lambda e:e.update(export_failures=1000))
    def test_error_rate_percent(self):self.bad(lambda e:e.update(error_rate_percent=1000))
    def test_rpo_minutes(self):self.bad(lambda e:e.update(rpo_minutes=1000))
    def test_rto_minutes(self):self.bad(lambda e:e.update(rto_minutes=1000))
    def test_policy_max_critical_findings(self):
        p=copy.deepcopy(POLICY);p['max_critical_findings']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_telemetry_age_minutes(self):
        p=copy.deepcopy(POLICY);p['max_telemetry_age_minutes']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_drift_age_minutes(self):
        p=copy.deepcopy(POLICY);p['max_drift_age_minutes']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_export_failures(self):
        p=copy.deepcopy(POLICY);p['max_export_failures']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_error_rate_percent(self):
        p=copy.deepcopy(POLICY);p['max_error_rate_percent']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_rpo_minutes(self):
        p=copy.deepcopy(POLICY);p['max_rpo_minutes']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_rto_minutes(self):
        p=copy.deepcopy(POLICY);p['max_rto_minutes']=999;self.assertTrue(validate(SAFE,p))
if __name__=="__main__":unittest.main()
