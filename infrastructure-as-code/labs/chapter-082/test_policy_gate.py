import copy,json,unittest
from pathlib import Path
from policy_gate import validate
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/safe.json').read_text())
POLICY=json.loads((ROOT/'policy.json').read_text())
class PolicyTests(unittest.TestCase):
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
    def test_policy_max_destroy(self):
        p=copy.deepcopy(POLICY);p['max_destroy']=10;self.assertTrue(validate(SAFE,p))
    def test_policy_max_replace(self):
        p=copy.deepcopy(POLICY);p['max_replace']=10;self.assertTrue(validate(SAFE,p))
    def test_policy_exact(self):
        p=copy.deepcopy(POLICY);p['require_exact_controls']=False;self.assertTrue(validate(SAFE,p))
    def test_schema(self):self.bad(lambda e:e.update(schema_version=2))
    def test_ticket(self):self.bad(lambda e:e.update(ticket='APPROVED'))
    def test_digest(self):self.bad(lambda e:e.update(artifact_digest='latest'))
    def test_destroy(self):self.bad(lambda e:e.update(destroy_count=1))
    def test_replace(self):self.bad(lambda e:e.update(replace_count=1))
    def test_missing_controls(self):self.bad(lambda e:e.pop('controls'))
    def test_extra_control(self):self.bad(lambda e:e['controls'].update(bypass=True))
    def test_invalid_exceptions(self):self.bad(lambda e:e.update(exceptions=None))
    def test_target_environment(self):self.bad(lambda e:e.update(environment='production'))
    def test_target_aws_account(self):self.bad(lambda e:e.update(aws_account='production'))
    def test_target_azure_subscription(self):self.bad(lambda e:e.update(azure_subscription='production'))
    def test_target_gcp_project(self):self.bad(lambda e:e.update(gcp_project='production'))
    def test_target_kube_context(self):self.bad(lambda e:e.update(kube_context='production'))
    def test_target_policy_version(self):self.bad(lambda e:e.update(policy_version='production'))
    def test_control_signed_source(self):self.bad(lambda e:e['controls'].update(signed_source=False))
    def test_control_pinned_providers(self):self.bad(lambda e:e['controls'].update(pinned_providers=False))
    def test_control_artifact_verified(self):self.bad(lambda e:e['controls'].update(artifact_verified=False))
    def test_control_oidc_scoped(self):self.bad(lambda e:e['controls'].update(oidc_scoped=False))
    def test_control_least_privilege(self):self.bad(lambda e:e['controls'].update(least_privilege=False))
    def test_control_state_encrypted(self):self.bad(lambda e:e['controls'].update(state_encrypted=False))
    def test_control_state_versioned(self):self.bad(lambda e:e['controls'].update(state_versioned=False))
    def test_control_state_lock(self):self.bad(lambda e:e['controls'].update(state_lock=False))
    def test_control_secrets_redacted(self):self.bad(lambda e:e['controls'].update(secrets_redacted=False))
    def test_control_policy_bundle_verified(self):self.bad(lambda e:e['controls'].update(policy_bundle_verified=False))
    def test_control_policy_enforced(self):self.bad(lambda e:e['controls'].update(policy_enforced=False))
    def test_control_cloud_guardrails(self):self.bad(lambda e:e['controls'].update(cloud_guardrails=False))
    def test_control_k8s_admission(self):self.bad(lambda e:e['controls'].update(k8s_admission=False))
    def test_control_gitops_owner_verified(self):self.bad(lambda e:e['controls'].update(gitops_owner_verified=False))
    def test_control_dbre_approved(self):self.bad(lambda e:e['controls'].update(dbre_approved=False))
    def test_control_backup_verified(self):self.bad(lambda e:e['controls'].update(backup_verified=False))
    def test_control_restore_rehearsed(self):self.bad(lambda e:e['controls'].update(restore_rehearsed=False))
    def test_control_slo_healthy(self):self.bad(lambda e:e['controls'].update(slo_healthy=False))
    def test_control_audit_immutable(self):self.bad(lambda e:e['controls'].update(audit_immutable=False))
if __name__=="__main__":unittest.main()
