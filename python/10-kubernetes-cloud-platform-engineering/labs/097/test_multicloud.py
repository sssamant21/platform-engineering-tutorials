import json,unittest
from contextlib import redirect_stdout
from io import StringIO
from dataclasses import replace
from multicloud import Resource,GovernanceError,paginate,snapshot,drift,compliance,finops,fingerprint,gate,FakePager,examples,demo,main
class Tests(unittest.TestCase):
    def setUp(self):self.items=examples()
    def test_three_clouds(self):self.assertEqual({r.provider for r in self.items},{"aws","azure","gcp"})
    def test_valid(self):self.items[0].validate()
    def test_invalid_provider(self):
        with self.assertRaises(GovernanceError):replace(self.items[0],provider="unknown").validate()
    def test_invalid_scope(self):
        with self.assertRaises(GovernanceError):replace(self.items[0],scope="../bad").validate()
    def test_negative_cost(self):
        with self.assertRaises(GovernanceError):replace(self.items[0],monthly_cost_usd=-1).validate()
    def test_nan_cost(self):
        with self.assertRaises(GovernanceError):replace(self.items[0],monthly_cost_usd=float("nan")).validate()
    def test_invalid_storage(self):
        with self.assertRaises(GovernanceError):replace(self.items[0],storage_free_pct=101).validate()
    def test_azure_casefold(self):
        a=self.items[1]
        self.assertEqual(a.key(),replace(a,native_id=a.native_id.upper()).key())
    def test_aws_case_sensitive(self):
        a=self.items[0]
        self.assertNotEqual(a.key(),replace(a,native_id=a.native_id.upper()).key())
    def test_pagination(self):self.assertEqual(paginate(FakePager([1,2,3],1).fetch),[1,2,3])
    def test_empty(self):self.assertEqual(paginate(FakePager([]).fetch),[])
    def test_page_budget(self):
        with self.assertRaises(GovernanceError):paginate(FakePager([1,2,3],1).fetch,max_pages=2)
    def test_item_budget(self):
        with self.assertRaises(GovernanceError):paginate(FakePager([1,2,3],1).fetch,max_items=2)
    def test_pagination_loop(self):
        with self.assertRaises(GovernanceError):paginate(lambda token:{"items":[],"next":"loop"})
    def test_malformed(self):
        with self.assertRaises(GovernanceError):paginate(lambda token:{"items":None})
    def test_invalid_budget(self):
        with self.assertRaises(GovernanceError):paginate(FakePager([]).fetch,max_pages=0)
    def test_snapshot(self):self.assertEqual(len(snapshot(self.items)["resources"]),3)
    def test_duplicate(self):
        with self.assertRaises(GovernanceError):snapshot([self.items[0],self.items[0]])
    def test_bad_record(self):
        with self.assertRaises(GovernanceError):snapshot(["bad"])
    def test_added(self):self.assertEqual(drift(snapshot(self.items[:2]),snapshot(self.items))["added"],1)
    def test_removed(self):self.assertEqual(drift(snapshot(self.items),snapshot(self.items[:2]))["removed"],1)
    def test_partial_removal_unknown(self):
        r=drift(snapshot(self.items),snapshot(self.items[:2],complete=False))
        self.assertIsNone(r["removed"])
    def test_changed(self):
        updated=[replace(self.items[0],owner="new")]+self.items[1:]
        self.assertEqual(drift(snapshot(self.items),snapshot(updated))["changed"],1)
    def test_unchanged(self):self.assertEqual(drift(snapshot(self.items),snapshot(self.items))["changed"],0)
    def test_owner_finding(self):self.assertIn("production-owner-required",{x["rule"] for x in compliance(self.items)})
    def test_cost_center(self):self.assertIn("cost-center-required",{x["rule"] for x in compliance(self.items)})
    def test_storage(self):self.assertIn("storage-capacity-review",{x["rule"] for x in compliance(self.items)})
    def test_compliant(self):
        a=replace(self.items[0],storage_free_pct=60)
        self.assertEqual(compliance([a]),[])
    def test_cost(self):self.assertEqual(finops(self.items)["estimated_monthly_usd"],470)
    def test_provider_cost(self):self.assertEqual(finops(self.items)["by_provider"]["aws"],200)
    def test_fingerprint(self):self.assertEqual(fingerprint(self.items),fingerprint(list(reversed(self.items))))
    def test_destructive(self):
        with self.assertRaises(GovernanceError):fingerprint(self.items,"delete")
    def test_gate_default(self):self.assertEqual(gate(self.items)["action"],"hold")
    def test_gate_approved(self):
        a={"approved":True,"digest":fingerprint(self.items),"rollback_tested":True,"owner":"oncall"}
        self.assertEqual(gate(self.items,a)["action"],"advisory-only")
    def test_wrong_digest(self):
        a={"approved":True,"digest":"wrong","rollback_tested":True,"owner":"oncall"}
        self.assertFalse(gate(self.items,a)["approved"])
    def test_missing_rollback(self):
        a={"approved":True,"digest":fingerprint(self.items),"rollback_tested":False,"owner":"oncall"}
        self.assertFalse(gate(self.items,a)["approved"])
    def test_zero_writes(self):self.assertEqual(gate(self.items,dry_run=False)["mutations"],0)
    def test_demo(self):self.assertEqual(demo()["inventory_count"],3)
    def test_partial_demo(self):self.assertEqual(demo(True)["drift"]["removal_status"],"unknown")
    def test_cli(self):
        output=StringIO()
        with redirect_stdout(output):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(output.getvalue())["network_calls"],0)
if __name__=="__main__":unittest.main()
