import copy,json,unittest
from pathlib import Path
from billing_gate import validate
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/safe.json').read_text())
POLICY=json.loads((ROOT/'policy.json').read_text())
class BillingTests(unittest.TestCase):
    def bad(self,fn):
        d=copy.deepcopy(SAFE);fn(d);self.assertTrue(validate(d,POLICY))
    def test_safe(self):self.assertEqual(validate(SAFE,POLICY),[])
    def test_unsafe(self):self.assertTrue(validate(json.loads((ROOT/'fixtures/unsafe.json').read_text()),POLICY))
    def test_doc(self):self.assertTrue(validate(None,POLICY))
    def test_policy(self):self.assertTrue(validate(SAFE,None))
    def test_schema(self):self.bad(lambda d:d.update(schema_version=2))
    def test_stale(self):self.bad(lambda d:d.update(export_age_hours=49))
    def test_age_bool(self):self.bad(lambda d:d.update(export_age_hours=True))
    def test_empty(self):self.bad(lambda d:d.update(days=[]))
    def test_short(self):self.bad(lambda d:d.update(days=d['days'][:6]))
    def test_row(self):self.bad(lambda d:d['days'].append(None))
    def test_duplicate(self):self.bad(lambda d:d['days'][2].update(day=d['days'][1]['day']))
    def test_gap(self):self.bad(lambda d:d['days'][2].update(day='2026-10-12'))
    def test_bad_date(self):self.bad(lambda d:d['days'][2].update(day='2026-02-30'))
    def test_source(self):self.bad(lambda d:d['days'][0].update(source_id='wrong'))
    def test_owner(self):self.bad(lambda d:d['days'][0].update(owner='unknown'))
    def test_negative(self):self.bad(lambda d:d['days'][0].update(cost_usd='-1'))
    def test_nan(self):self.bad(lambda d:d['days'][0].update(cost_usd='NaN'))
    def test_bool(self):self.bad(lambda d:d['days'][0].update(cost_usd=True))
    def test_policy_schema(self):
        p=copy.deepcopy(POLICY);p['schema_version']=2;self.assertTrue(validate(SAFE,p))
    def test_policy_target(self):
        p=copy.deepcopy(POLICY);p['target']={};self.assertTrue(validate(SAFE,p))
    def test_policy_age(self):
        p=copy.deepcopy(POLICY);p['max_export_age_hours']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_min(self):
        p=copy.deepcopy(POLICY);p['min_days']=1;self.assertTrue(validate(SAFE,p))
    def test_policy_max(self):
        p=copy.deepcopy(POLICY);p['max_days']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_threshold(self):
        p=copy.deepcopy(POLICY);p['thresholds']=[100];self.assertTrue(validate(SAFE,p))
    def test_target_environment(self):self.bad(lambda d:d.update(environment='wrong'))
    def test_target_billing_account(self):self.bad(lambda d:d.update(billing_account='wrong'))
    def test_target_currency(self):self.bad(lambda d:d.update(currency='wrong'))
    def test_target_cost_basis(self):self.bad(lambda d:d.update(cost_basis='wrong'))
    def test_target_owner(self):self.bad(lambda d:d.update(owner='wrong'))
    def test_target_repository(self):self.bad(lambda d:d.update(repository='wrong'))
if __name__=="__main__":unittest.main()
