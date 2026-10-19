import copy,json,unittest
from pathlib import Path
from ledger_gate import validate
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/safe.json').read_text())
POLICY=json.loads((ROOT/'policy.json').read_text())
class LedgerTests(unittest.TestCase):
    def bad(self,fn):
        d=copy.deepcopy(SAFE);fn(d);self.assertTrue(validate(d,POLICY))
    def test_safe(self):self.assertEqual(validate(SAFE,POLICY),[])
    def test_unsafe(self):self.assertTrue(validate(json.loads((ROOT/'fixtures/unsafe.json').read_text()),POLICY))
    def test_invalid_doc(self):self.assertTrue(validate(None,POLICY))
    def test_invalid_policy(self):self.assertTrue(validate(SAFE,None))
    def test_schema(self):self.bad(lambda d:d.update(schema_version=2))
    def test_stale(self):self.bad(lambda d:d.update(export_age_hours=73))
    def test_age_bool(self):self.bad(lambda d:d.update(export_age_hours=True))
    def test_empty(self):self.bad(lambda d:d.update(records=[]))
    def test_bad_row(self):self.bad(lambda d:d['records'].append(None))
    def test_duplicate(self):self.bad(lambda d:d['records'].append(d['records'][0]))
    def test_line_id(self):self.bad(lambda d:d['records'][0].update(line_id='?'))
    def test_kind(self):self.bad(lambda d:d['records'][0].update(kind='unknown'))
    def test_negative(self):self.bad(lambda d:d['records'][0].update(cents=-1))
    def test_bool_cents(self):self.bad(lambda d:d['records'][0].update(cents=True))
    def test_float_cents(self):self.bad(lambda d:d['records'][0].update(cents=2.5))
    def test_provider(self):self.bad(lambda d:d['records'][0].update(provider='unknown'))
    def test_export(self):self.bad(lambda d:d['records'][0].update(export_id=''))
    def test_digest(self):self.bad(lambda d:d['records'][0].update(source_digest='invalid'))
    def test_missing_tags(self):self.bad(lambda d:d['records'][0].pop('tags'))
    def test_extra_tags(self):self.bad(lambda d:d['records'][0]['tags'].update(extra='wrong'))
    def test_missing_weights(self):self.bad(lambda d:d['records'][1].pop('weights'))
    def test_empty_shared(self):self.bad(lambda d:d['records'][1].update(weights={}))
    def test_negative_weight(self):self.bad(lambda d:d['records'][1].update(weights={'payments':-1}))
    def test_bool_weight(self):self.bad(lambda d:d['records'][1].update(weights={'payments':True}))
    def test_direct_weight(self):self.bad(lambda d:d['records'][0].update(weights={'payments':1}))
    def test_unallocated_weight(self):self.bad(lambda d:d['records'][2].update(weights={'payments':1}))
    def test_policy_schema(self):
        p=copy.deepcopy(POLICY);p['schema_version']=2;self.assertTrue(validate(SAFE,p))
    def test_policy_target(self):
        p=copy.deepcopy(POLICY);p['target']={};self.assertTrue(validate(SAFE,p))
    def test_policy_kinds(self):
        p=copy.deepcopy(POLICY);p['accepted_kinds']=[];self.assertTrue(validate(SAFE,p))
    def test_policy_tags(self):
        p=copy.deepcopy(POLICY);p['required_tags']=[];self.assertTrue(validate(SAFE,p))
    def test_policy_age(self):
        p=copy.deepcopy(POLICY);p['max_export_age_hours']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_unique(self):
        p=copy.deepcopy(POLICY);p['require_unique_lines']=False;self.assertTrue(validate(SAFE,p))
    def test_target_environment(self):self.bad(lambda d:d.update(environment='wrong'))
    def test_row_environment(self):self.assertEqual(validate(SAFE,POLICY),[])
    def test_target_billing_account(self):self.bad(lambda d:d.update(billing_account='wrong'))
    def test_row_billing_account(self):self.bad(lambda d:d['records'][0].update(billing_account='wrong'))
    def test_target_usage_month(self):self.bad(lambda d:d.update(usage_month='wrong'))
    def test_row_usage_month(self):self.bad(lambda d:d['records'][0].update(usage_month='wrong'))
    def test_target_currency(self):self.bad(lambda d:d.update(currency='wrong'))
    def test_row_currency(self):self.bad(lambda d:d['records'][0].update(currency='wrong'))
    def test_target_cost_basis(self):self.bad(lambda d:d.update(cost_basis='wrong'))
    def test_row_cost_basis(self):self.bad(lambda d:d['records'][0].update(cost_basis='wrong'))
    def test_target_repository(self):self.bad(lambda d:d.update(repository='wrong'))
    def test_row_repository(self):self.assertEqual(validate(SAFE,POLICY),[])
    def test_tag_owner(self):self.bad(lambda d:d['records'][0]['tags'].update(owner=''))
    def test_tag_cost_center(self):self.bad(lambda d:d['records'][0]['tags'].update(cost_center=''))
    def test_tag_application(self):self.bad(lambda d:d['records'][0]['tags'].update(application=''))
if __name__=="__main__":unittest.main()
