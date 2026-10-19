import json,math,unittest
from io import StringIO
from contextlib import redirect_stdout
from resilience_lab import ResilienceError,backoff,retry_plan,Breaker,bulkhead,timeout_budget,chaos_gate,sli,scenario,demo,main
class Tests(unittest.TestCase):
    def reject(self,fn):
        with self.assertRaises(ResilienceError):fn()
    def test_backoff_first(self):self.assertEqual(backoff(0),100)
    def test_backoff_exponential(self):self.assertEqual(backoff(3),800)
    def test_backoff_cap(self):self.assertEqual(backoff(20),5000)
    def test_backoff_jitter(self):self.assertEqual(backoff(2,jitter=.5),backoff(2,jitter=.5))
    def test_backoff_bounded(self):self.assertLessEqual(backoff(10,cap_ms=100,jitter=1),100)
    def test_backoff_bad_attempt(self):self.reject(lambda:backoff(-1))
    def test_backoff_bad_jitter(self):self.reject(lambda:backoff(0,jitter=1.2))
    def test_backoff_nan(self):self.reject(lambda:backoff(0,jitter=math.nan))
    def test_retry_success(self):self.assertEqual(retry_plan(1,3)["status"],"success")
    def test_retry_exhausted(self):self.assertEqual(retry_plan(5,2)["status"],"exhausted")
    def test_retry_nonidempotent(self):self.assertEqual(retry_plan(1,3,False)["status"],"blocked-non-idempotent")
    def test_retry_deadline(self):self.assertEqual(retry_plan(2,4,deadline_ms=50)["status"],"deadline")
    def test_retry_attempts(self):self.reject(lambda:retry_plan(1,0))
    def test_retry_bad_failures(self):self.reject(lambda:retry_plan(-1))
    def test_retry_no_writes(self):self.assertEqual(retry_plan(1)["mutations"],0)
    def test_breaker_closed(self):self.assertEqual(Breaker().state,"closed")
    def test_breaker_opens(self):
        b=Breaker(2,10);b.record(False,1);self.assertEqual(b.record(False,2),"open")
    def test_breaker_rejects(self):
        b=Breaker(1,10);b.record(False,1);self.assertFalse(b.allow(2))
    def test_breaker_halfopen(self):
        b=Breaker(1,10);b.record(False,1);self.assertTrue(b.allow(11));self.assertEqual(b.state,"half-open")
    def test_breaker_recover(self):
        b=Breaker(1,10);b.record(False,1);b.record(True,11);self.assertEqual(b.state,"closed")
    def test_breaker_reopen(self):
        b=Breaker(1,10);b.record(False,1);b.record(False,11);self.assertEqual(b.state,"open")
    def test_breaker_bad_threshold(self):self.reject(lambda:Breaker(0))
    def test_breaker_bad_time(self):self.reject(lambda:Breaker().allow(-1))
    def test_bulkhead(self):self.assertEqual(bulkhead(20,5,3)["rejected"],12)
    def test_bulkhead_no_reject(self):self.assertEqual(bulkhead(2,5,3)["rejected"],0)
    def test_bulkhead_bad(self):self.reject(lambda:bulkhead(1,0,0))
    def test_timeout_fits(self):self.assertTrue(timeout_budget(1000,100,200,2)["fits"])
    def test_timeout_exceeds(self):self.assertFalse(timeout_budget(500,100,200,2)["fits"])
    def test_timeout_bad(self):self.reject(lambda:timeout_budget(0,100,200))
    def test_chaos_allowed_staging(self):self.assertEqual(chaos_gate("staging",True,True,True,10,2)["decision"],"simulation-authorized")
    def test_chaos_production_block(self):self.assertEqual(chaos_gate("production",True,True,True,10,2)["decision"],"hold")
    def test_chaos_approval(self):self.assertEqual(chaos_gate("staging",False,True,True,10,2)["decision"],"hold")
    def test_chaos_rollback(self):self.assertEqual(chaos_gate("staging",True,False,True,10,2)["decision"],"hold")
    def test_chaos_unhealthy(self):self.assertEqual(chaos_gate("staging",True,True,False,10,2)["decision"],"hold")
    def test_chaos_budget(self):self.assertEqual(chaos_gate("staging",True,True,True,0,2)["decision"],"hold")
    def test_chaos_radius(self):self.assertEqual(chaos_gate("staging",True,True,True,10,10)["decision"],"hold")
    def test_chaos_bad_radius(self):self.reject(lambda:chaos_gate("staging",True,True,True,10,0))
    def test_chaos_no_fault(self):self.assertEqual(chaos_gate("staging",True,True,True,10,2)["faults_injected"],0)
    def test_sli_good(self):self.assertEqual(sli(100,100,.99)["status"],"within-budget")
    def test_sli_breached(self):self.assertEqual(sli(90,100,.99)["status"],"breached")
    def test_sli_zero(self):self.assertEqual(sli(0,0)["status"],"unknown")
    def test_sli_bad(self):self.reject(lambda:sli(101,100))
    def test_scenario(self):self.assertEqual(scenario("db",1,3,2,1,4)["bulkhead"]["rejected"],1)
    def test_scenario_bad(self):self.reject(lambda:scenario("",1,3,2,1,4))
    def test_demo_no_writes(self):self.assertEqual(demo()["mutations"],0)
    def test_demo_no_network(self):self.assertEqual(demo()["network_calls"],0)
    def test_cli(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(out.getvalue())["chaos"]["faults_injected"],0)
if __name__=="__main__":unittest.main()
