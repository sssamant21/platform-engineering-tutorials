import asyncio,json,math,unittest
from io import StringIO
from contextlib import redirect_stdout
from performance_lab import PerfError,percentile,summary,budget,slow_count,fast_count,cpu_profile,memory_profile,benchmark,io_async,async_batch,threaded_io,Incident,demo,main
class Tests(unittest.TestCase):
    def reject(self,fn):
        with self.assertRaises(PerfError):fn()
    def test_p0(self):self.assertEqual(percentile([10,20,30],0),10)
    def test_p100(self):self.assertEqual(percentile([10,20,30],100),30)
    def test_p50(self):self.assertEqual(percentile([10,20,30],50),20)
    def test_p95(self):self.assertAlmostEqual(percentile([0,100],95),95)
    def test_p99(self):self.assertAlmostEqual(percentile([0,100],99),99)
    def test_single(self):self.assertEqual(percentile([4],99),4)
    def test_unsorted(self):self.assertEqual(percentile([30,10,20],50),20)
    def test_empty(self):self.reject(lambda:percentile([],50))
    def test_negative(self):self.reject(lambda:percentile([-1],50))
    def test_nan(self):self.reject(lambda:percentile([math.nan],50))
    def test_inf(self):self.reject(lambda:percentile([math.inf],50))
    def test_invalid_p(self):self.reject(lambda:percentile([1],101))
    def test_summary(self):self.assertEqual(summary([1,2,3])["count"],3)
    def test_mean(self):self.assertEqual(summary([1,2,3])["mean_ms"],2)
    def test_budget_pass(self):self.assertTrue(budget([1,2,3])["pass"])
    def test_budget_fail(self):self.assertFalse(budget([100,200,300],100,200)["pass"])
    def test_bad_budget(self):self.reject(lambda:budget([1],0,2))
    def test_slow_fast_equal(self):
        x=[1,2,2,3,3,3];self.assertEqual(slow_count(x),fast_count(x))
    def test_empty_count(self):self.assertEqual(fast_count([]),0)
    def test_cpu_profile(self):
        r=cpu_profile(fast_count,[1,2,2]);self.assertEqual(r["result"],3);self.assertIn("function calls",r["profile_excerpt"])
    def test_memory_profile(self):
        r=memory_profile(fast_count,[1,2,2]);self.assertEqual(r["result"],3);self.assertGreaterEqual(r["peak_traced_bytes"],0)
    def test_benchmark(self):self.assertEqual(benchmark(fast_count,[1,2],3)["count"],3)
    def test_bad_iterations(self):self.reject(lambda:benchmark(fast_count,[1],0))
    def test_async(self):self.assertEqual(asyncio.run(io_async()),"ok")
    def test_async_batch(self):self.assertEqual(asyncio.run(async_batch(3)),["ok"]*3)
    def test_bad_async_batch(self):
        with self.assertRaises(PerfError):asyncio.run(async_batch(0))
    def test_bad_delay(self):
        with self.assertRaises(PerfError):asyncio.run(io_async(-1))
    def test_threaded(self):self.assertEqual(threaded_io(3),["ok"]*3)
    def test_bad_threaded(self):self.reject(lambda:threaded_io(0))
    def test_incident_regression(self):self.assertTrue(Incident("api",50,120,50,50).evaluate()["latency_regression"])
    def test_incident_cpu(self):self.assertTrue(Incident("api",50,60,90,50).evaluate()["cpu_pressure"])
    def test_incident_memory(self):self.assertTrue(Incident("api",50,60,50,95).evaluate()["memory_pressure"])
    def test_incident_clean(self):self.assertFalse(Incident("api",50,60,50,50).evaluate()["cpu_pressure"])
    def test_incident_zero_baseline(self):self.reject(lambda:Incident("api",0,10,50,50).evaluate())
    def test_incident_bad_cpu(self):self.reject(lambda:Incident("api",10,20,101,50).evaluate())
    def test_incident_nan(self):self.reject(lambda:Incident("api",10,math.nan,50,50).evaluate())
    def test_no_mutation(self):self.assertEqual(demo()["mutations"],0)
    def test_no_network(self):self.assertEqual(demo()["network_calls"],0)
    def test_cli(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--dry-run"]),0)
        self.assertIn("synthetic_latency",json.loads(out.getvalue()))
    def test_profile_cli(self):
        out=StringIO()
        with redirect_stdout(out):main(["--profile"])
        self.assertIn("cprofile",json.loads(out.getvalue()))
if __name__=="__main__":unittest.main()
