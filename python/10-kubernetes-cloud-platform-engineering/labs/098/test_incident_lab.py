import unittest,json
from dataclasses import replace
from io import StringIO
from contextlib import redirect_stdout
from incident_lab import Signal,LabError,normalize,paginate,slo,correlate,plan,gate,FakePager,demo,main
class Tests(unittest.TestCase):
    def setUp(self):self.s=Signal("aws","123","api","errors",5,1000,"critical","a"*32)
    def reject(self,fn):
        with self.assertRaises(LabError):fn()
    def test_valid(self):self.s.validate()
    def test_provider(self):self.reject(lambda:replace(self.s,provider="bad").validate())
    def test_nan(self):self.reject(lambda:replace(self.s,value=float("nan")).validate())
    def test_negative(self):self.reject(lambda:replace(self.s,value=-1).validate())
    def test_trace(self):self.reject(lambda:replace(self.s,trace_id="bad").validate())
    def test_severity(self):self.reject(lambda:replace(self.s,severity="unknown").validate())
    def test_normalize(self):self.assertEqual(len(normalize([vars(self.s)],1100)),1)
    def test_stale(self):self.reject(lambda:normalize([vars(self.s)],1400))
    def test_future(self):self.reject(lambda:normalize([vars(self.s)],999))
    def test_malformed(self):self.reject(lambda:normalize([{"bad":1}],1100))
    def test_pages(self):self.assertEqual(paginate(FakePager([1,2,3],1).fetch),[1,2,3])
    def test_empty(self):self.assertEqual(paginate(FakePager([]).fetch),[])
    def test_page_limit(self):self.reject(lambda:paginate(FakePager([1,2,3],1).fetch,max_pages=2))
    def test_item_limit(self):self.reject(lambda:paginate(FakePager([1,2,3],1).fetch,max_items=2))
    def test_loop(self):self.reject(lambda:paginate(lambda t:{"items":[],"next":"same"}))
    def test_bad_page(self):self.reject(lambda:paginate(lambda t:{"items":None}))
    def test_slo_good(self):self.assertFalse(slo(9999,10000)["breached"])
    def test_slo_bad(self):self.assertTrue(slo(9900,10000)["breached"])
    def test_slo_invalid(self):self.reject(lambda:slo(11,10))
    def test_slo_empty(self):self.reject(lambda:slo(0,0))
    def test_slo_burn(self):self.assertGreater(slo(9900,10000)["burn_ratio"],1)
    def test_dedup(self):self.assertEqual(correlate([self.s,self.s])[0]["alerts"],1)
    def test_multi_cloud(self):
        other=replace(self.s,provider="azure",scope="sub",metric="latency")
        self.assertEqual(correlate([self.s,other])[0]["providers"],["aws","azure"])
    def test_no_causality(self):self.assertEqual(correlate([self.s])[0]["causality"],"not-established")
    def test_separate_window(self):self.assertEqual(len(correlate([self.s,replace(self.s,timestamp=1500)])),2)
    def test_separate_service(self):self.assertEqual(len(correlate([self.s,replace(self.s,service="db")])),2)
    def test_window(self):self.reject(lambda:correlate([self.s],0))
    def test_plan_stable(self):
        i=correlate([self.s])[0]
        self.assertEqual(plan(i),plan(dict(reversed(list(i.items())))))
    def test_no_restart(self):self.reject(lambda:plan({"id":"x"},"restart-db"))
    def test_hold(self):self.assertEqual(gate({"id":"x"})["action"],"hold")
    def test_approval(self):
        i={"id":"x"};a={"approved":True,"digest":plan(i),"rollback_tested":True,"owner":"oncall"}
        self.assertEqual(gate(i,a)["action"],"advisory-only")
    def test_wrong_digest(self):self.assertFalse(gate({"id":"x"},{"approved":True,"digest":"bad","rollback_tested":True,"owner":"x"})["approved"])
    def test_rollback(self):
        i={"id":"x"}
        self.assertFalse(gate(i,{"approved":True,"digest":plan(i),"rollback_tested":False,"owner":"x"})["approved"])
    def test_no_writes(self):self.assertEqual(gate({"id":"x"},dry_run=False)["mutations"],0)
    def test_demo(self):self.assertEqual(demo()["signals"],3)
    def test_cli(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(out.getvalue())["network_calls"],0)
if __name__=="__main__":unittest.main()
