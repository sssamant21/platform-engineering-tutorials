import copy,json,unittest
from pathlib import Path
from billing_gate import validate
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/safe.json').read_text())
POLICY=json.loads((ROOT/'policy.json').read_text())
class BillingGateTests(unittest.TestCase):
    def bad(self,fn):
        e=copy.deepcopy(SAFE);fn(e);self.assertTrue(validate(e,POLICY))
    def test_safe(self):self.assertEqual(validate(SAFE,POLICY),[])
    def test_unsafe(self):self.assertTrue(validate(json.loads((ROOT/'fixtures/unsafe.json').read_text()),POLICY))
    def test_invalid_doc(self):self.assertTrue(validate([],POLICY))
    def test_invalid_policy(self):self.assertTrue(validate(SAFE,[]))
    def test_schema(self):self.bad(lambda e:e.update(schema_version=2))
    def test_stale(self):self.bad(lambda e:e.update(export_age_hours=49))
    def test_age_boolean(self):self.bad(lambda e:e.update(export_age_hours=True))
    def test_empty_rows(self):self.bad(lambda e:e.update(records=[]))
    def test_bad_row(self):self.bad(lambda e:e['records'].append(None))
    def test_duplicate(self):self.bad(lambda e:e['records'].append(e['records'][0]))
    def test_bad_line_id(self):self.bad(lambda e:e['records'][0].update(line_id='?'))
    def test_provider(self):self.bad(lambda e:e['records'][0].update(provider='unknown'))
    def test_currency(self):self.bad(lambda e:e['records'][0].update(currency='EUR'))
    def test_basis(self):self.bad(lambda e:e['records'][0].update(cost_basis='unblended'))
    def test_digest(self):self.bad(lambda e:e['records'][0].update(source_digest='sha256:bad'))
    def test_negative(self):self.bad(lambda e:e['records'][0].update(cost_usd=-1))
    def test_nan(self):self.bad(lambda e:e['records'][0].update(cost_usd='NaN'))
    def test_bool(self):self.bad(lambda e:e['records'][0].update(cost_usd=True))
    def test_empty_service(self):self.bad(lambda e:e['records'][0].update(service=''))
    def test_empty_resource(self):self.bad(lambda e:e['records'][0].update(resource_id=''))
    def test_empty_export(self):self.bad(lambda e:e['records'][0].update(export_id=''))
    def test_missing_tags(self):self.bad(lambda e:e['records'][0].pop('tags'))
    def test_extra_tag(self):self.bad(lambda e:e['records'][0]['tags'].update(extra='bad'))
    def test_policy_schema(self):
        p=copy.deepcopy(POLICY);p['schema_version']=2;self.assertTrue(validate(SAFE,p))
    def test_policy_target(self):
        p=copy.deepcopy(POLICY);p['target']={};self.assertTrue(validate(SAFE,p))
    def test_policy_currency(self):
        p=copy.deepcopy(POLICY);p['currency']='EUR';self.assertTrue(validate(SAFE,p))
    def test_policy_basis(self):
        p=copy.deepcopy(POLICY);p['cost_basis']='unblended';self.assertTrue(validate(SAFE,p))
    def test_policy_providers(self):
        p=copy.deepcopy(POLICY);p['accepted_providers']=[];self.assertTrue(validate(SAFE,p))
    def test_policy_required_tags(self):
        p=copy.deepcopy(POLICY);p['required_tags']=[];self.assertTrue(validate(SAFE,p))
    def test_policy_age(self):
        p=copy.deepcopy(POLICY);p['max_export_age_hours']=999;self.assertTrue(validate(SAFE,p))
    def test_policy_allocation(self):
        p=copy.deepcopy(POLICY);p['max_unallocated_percent']=100;self.assertTrue(validate(SAFE,p))
    def test_policy_unique(self):
        p=copy.deepcopy(POLICY);p['require_unique_lines']=False;self.assertTrue(validate(SAFE,p))
    def test_target_environment(self):self.bad(lambda e:e.update(environment='wrong'))
    def test_target_account(self):self.bad(lambda e:e.update(account='wrong'))
    def test_target_repository(self):self.bad(lambda e:e.update(repository='wrong'))
    def test_target_owner(self):self.bad(lambda e:e.update(owner='wrong'))
    def test_target_usage_date(self):self.bad(lambda e:e.update(usage_date='wrong'))
    def test_tag_owner(self):self.bad(lambda e:e['records'][0]['tags'].update(owner=''))
    def test_tag_environment(self):self.bad(lambda e:e['records'][0]['tags'].update(environment=''))
    def test_tag_cost_center(self):self.bad(lambda e:e['records'][0]['tags'].update(cost_center=''))
    def test_tag_application(self):self.bad(lambda e:e['records'][0]['tags'].update(application=''))
    def test_tag_managed_by(self):self.bad(lambda e:e['records'][0]['tags'].update(managed_by=''))
if __name__=="__main__":unittest.main()
