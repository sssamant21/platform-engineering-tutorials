import copy,json,unittest
from pathlib import Path
from evidence_gate import validate
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/safe.json').read_text())
POLICY=json.loads((ROOT/'policy.json').read_text())
class EvidenceTests(unittest.TestCase):
    def bad(self,fn):
        d=copy.deepcopy(SAFE);fn(d);self.assertTrue(validate(d,POLICY))
    def test_safe(self):self.assertEqual(validate(SAFE,POLICY),[])
    def test_unsafe(self):self.assertTrue(validate(json.loads((ROOT/'fixtures/unsafe.json').read_text()),POLICY))
    def test_doc(self):self.assertTrue(validate(None,POLICY))
    def test_policy(self):self.assertTrue(validate(SAFE,None))
    def test_schema(self):self.bad(lambda d:d.update(schema_version=2))
    def test_stale(self):self.bad(lambda d:d.update(export_age_hours=49))
    def test_age_bool(self):self.bad(lambda d:d.update(export_age_hours=True))
    def test_negative_baseline(self):self.bad(lambda d:d.update(baseline_monthly_usd='-1'))
    def test_zero_baseline(self):self.bad(lambda d:d.update(baseline_monthly_usd='0'))
    def test_nan_baseline(self):self.bad(lambda d:d.update(baseline_monthly_usd='NaN'))
    def test_negative_target(self):self.bad(lambda d:d.update(target_monthly_usd='-1'))
    def test_nan_target(self):self.bad(lambda d:d.update(target_monthly_usd='NaN'))
    def test_cpu(self):self.bad(lambda d:d.update(cpu_p99_pct=101))
    def test_memory(self):self.bad(lambda d:d.update(memory_p99_pct=-1))
    def test_headroom(self):self.bad(lambda d:d.update(headroom_pct=19))
    def test_bool_headroom(self):self.bad(lambda d:d.update(headroom_pct=True))
    def test_resource(self):self.bad(lambda d:d.update(resource_id='prod-rds'))
    def test_digest(self):self.bad(lambda d:d.update(source_digest='invalid'))
    def test_policy_schema(self):
        p=copy.deepcopy(POLICY);p['schema_version']=2;self.assertTrue(validate(SAFE,p))
    def test_policy_target(self):
        p=copy.deepcopy(POLICY);p['target']={};self.assertTrue(validate(SAFE,p))
    def test_policy_age(self):
        p=copy.deepcopy(POLICY);p['max_age_hours']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_headroom(self):
        p=copy.deepcopy(POLICY);p['minimum_headroom_pct']=0;self.assertTrue(validate(SAFE,p))
    def test_target_environment(self):self.bad(lambda d:d.update(environment='wrong'))
    def test_target_billing_account(self):self.bad(lambda d:d.update(billing_account='wrong'))
    def test_target_currency(self):self.bad(lambda d:d.update(currency='wrong'))
    def test_target_cost_basis(self):self.bad(lambda d:d.update(cost_basis='wrong'))
    def test_target_owner(self):self.bad(lambda d:d.update(owner='wrong'))
    def test_target_repository(self):self.bad(lambda d:d.update(repository='wrong'))
    def test_guard_forecast_complete(self):self.bad(lambda d:d.update(forecast_complete=False))
    def test_guard_backup_verified(self):self.bad(lambda d:d.update(backup_verified=False))
    def test_guard_slo_healthy(self):self.bad(lambda d:d.update(slo_healthy=False))
    def test_guard_rpo_healthy(self):self.bad(lambda d:d.update(rpo_healthy=False))
    def test_guard_rto_healthy(self):self.bad(lambda d:d.update(rto_healthy=False))
    def test_guard_rollback_tested(self):self.bad(lambda d:d.update(rollback_tested=False))
if __name__=="__main__":unittest.main()
