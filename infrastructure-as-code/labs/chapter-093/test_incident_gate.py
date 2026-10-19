import copy,json,unittest
from pathlib import Path
from incident_gate import validate
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/safe.json').read_text())
POLICY=json.loads((ROOT/'policy.json').read_text())
class IncidentGateTests(unittest.TestCase):
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
    def test_control_change_ticket_verified(self):self.bad(lambda e:e['controls'].update(change_ticket_verified=False))
    def test_control_actor_identity_verified(self):self.bad(lambda e:e['controls'].update(actor_identity_verified=False))
    def test_control_plan_digest_verified(self):self.bad(lambda e:e['controls'].update(plan_digest_verified=False))
    def test_control_provider_audit_enabled(self):self.bad(lambda e:e['controls'].update(provider_audit_enabled=False))
    def test_control_cloud_inventory_complete(self):self.bad(lambda e:e['controls'].update(cloud_inventory_complete=False))
    def test_control_otel_traces_present(self):self.bad(lambda e:e['controls'].update(otel_traces_present=False))
    def test_control_prometheus_metrics_fresh(self):self.bad(lambda e:e['controls'].update(prometheus_metrics_fresh=False))
    def test_control_gitops_health_observed(self):self.bad(lambda e:e['controls'].update(gitops_health_observed=False))
    def test_control_policy_enforced(self):self.bad(lambda e:e['controls'].update(policy_enforced=False))
    def test_control_state_snapshot_preserved(self):self.bad(lambda e:e['controls'].update(state_snapshot_preserved=False))
    def test_control_event_time_utc(self):self.bad(lambda e:e['controls'].update(event_time_utc=False))
    def test_control_clock_skew_bounded(self):self.bad(lambda e:e['controls'].update(clock_skew_bounded=False))
    def test_control_trace_context_propagated(self):self.bad(lambda e:e['controls'].update(trace_context_propagated=False))
    def test_control_slo_burn_rate_checked(self):self.bad(lambda e:e['controls'].update(slo_burn_rate_checked=False))
    def test_control_error_budget_reviewed(self):self.bad(lambda e:e['controls'].update(error_budget_reviewed=False))
    def test_control_incident_commander_assigned(self):self.bad(lambda e:e['controls'].update(incident_commander_assigned=False))
    def test_control_blast_radius_documented(self):self.bad(lambda e:e['controls'].update(blast_radius_documented=False))
    def test_control_alternative_hypotheses_reviewed(self):self.bad(lambda e:e['controls'].update(alternative_hypotheses_reviewed=False))
    def test_control_no_automatic_causal_claim(self):self.bad(lambda e:e['controls'].update(no_automatic_causal_claim=False))
    def test_control_no_auto_destroy(self):self.bad(lambda e:e['controls'].update(no_auto_destroy=False))
    def test_control_rollback_approved(self):self.bad(lambda e:e['controls'].update(rollback_approved=False))
    def test_control_dbre_backup_verified(self):self.bad(lambda e:e['controls'].update(dbre_backup_verified=False))
    def test_control_dbre_restore_rehearsed(self):self.bad(lambda e:e['controls'].update(dbre_restore_rehearsed=False))
    def test_control_rpo_accepted(self):self.bad(lambda e:e['controls'].update(rpo_accepted=False))
    def test_control_rto_accepted(self):self.bad(lambda e:e['controls'].update(rto_accepted=False))
    def test_control_slo_healthy(self):self.bad(lambda e:e['controls'].update(slo_healthy=False))
    def test_control_evidence_retained(self):self.bad(lambda e:e['controls'].update(evidence_retained=False))
    def test_control_postmortem_owner_assigned(self):self.bad(lambda e:e['controls'].update(postmortem_owner_assigned=False))
    def test_critical_findings(self):self.bad(lambda e:e.update(critical_findings=1000))
    def test_destructive_actions(self):self.bad(lambda e:e.update(destructive_actions=1000))
    def test_missing_evidence(self):self.bad(lambda e:e.update(missing_evidence=1000))
    def test_event_age_minutes(self):self.bad(lambda e:e.update(event_age_minutes=1000))
    def test_clock_skew_seconds(self):self.bad(lambda e:e.update(clock_skew_seconds=1000))
    def test_change_failure_rate_percent(self):self.bad(lambda e:e.update(change_failure_rate_percent=1000))
    def test_rpo_minutes(self):self.bad(lambda e:e.update(rpo_minutes=1000))
    def test_rto_minutes(self):self.bad(lambda e:e.update(rto_minutes=1000))
    def test_policy_max_critical_findings(self):
        p=copy.deepcopy(POLICY);p['max_critical_findings']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_destructive_actions(self):
        p=copy.deepcopy(POLICY);p['max_destructive_actions']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_missing_evidence(self):
        p=copy.deepcopy(POLICY);p['max_missing_evidence']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_event_age_minutes(self):
        p=copy.deepcopy(POLICY);p['max_event_age_minutes']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_clock_skew_seconds(self):
        p=copy.deepcopy(POLICY);p['max_clock_skew_seconds']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_change_failure_rate_percent(self):
        p=copy.deepcopy(POLICY);p['max_change_failure_rate_percent']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_rpo_minutes(self):
        p=copy.deepcopy(POLICY);p['max_rpo_minutes']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_max_rto_minutes(self):
        p=copy.deepcopy(POLICY);p['max_rto_minutes']=999;self.assertTrue(validate(SAFE,p))
if __name__=="__main__":unittest.main()
