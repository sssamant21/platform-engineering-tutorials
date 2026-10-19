import asyncio,json,math,threading,unittest
from io import StringIO
from contextlib import redirect_stdout
from concurrency_lab import ConcurrencyError,count,cpu_task,serial_cpu,threaded_cpu,process_cpu,thread_io,bounded_async,cancel_example,timeout_example,SafeCounter,backpressure,percentile,benchmark,Incident,demo,main
class Tests(unittest.TestCase):
    def reject(self,fn):
        with self.assertRaises(ConcurrencyError):fn()
    def test_limit(self):self.assertEqual(count(4),4)
    def test_limit_bool(self):self.reject(lambda:count(True))
    def test_limit_zero(self):self.reject(lambda:count(0))
    def test_limit_high(self):self.reject(lambda:count(65))
    def test_cpu(self):self.assertEqual(cpu_task(4),14)
    def test_cpu_zero(self):self.assertEqual(cpu_task(0),0)
    def test_cpu_invalid(self):self.reject(lambda:cpu_task(-1))
    def test_cpu_bool(self):self.reject(lambda:cpu_task(True))
    def test_thread_cpu(self):self.assertEqual(threaded_cpu([100,200],2),serial_cpu([100,200]))
    def test_process_cpu(self):self.assertEqual(process_cpu([100,200],2),serial_cpu([100,200]))
    def test_process_limit(self):self.reject(lambda:process_cpu([100],9))
    def test_thread_io(self):self.assertEqual(thread_io([1,2,3],2),[2,4,6])
    def test_thread_io_invalid(self):
        with self.assertRaises(ConcurrencyError):thread_io([-1])
    def test_async_io(self):self.assertEqual(asyncio.run(bounded_async([1,2,3],2))["values"],[2,4,6])
    def test_async_limit(self):self.assertLessEqual(asyncio.run(bounded_async(list(range(10)),3))["peak_inflight"],3)
    def test_async_zero_limit(self):
        with self.assertRaises(ConcurrencyError):asyncio.run(bounded_async([1],0))
    def test_async_invalid(self):
        with self.assertRaises(ConcurrencyError):asyncio.run(bounded_async([-1],2))
    def test_cancel(self):self.assertTrue(asyncio.run(cancel_example())["cancelled"])
    def test_timeout(self):self.assertTrue(asyncio.run(timeout_example())["timed_out"])
    def test_timeout_invalid(self):
        with self.assertRaises(ConcurrencyError):asyncio.run(timeout_example(-1))
    def test_counter(self):
        c=SafeCounter();threads=[threading.Thread(target=c.add,args=(1,)) for _ in range(20)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(c.value,20)
    def test_counter_invalid(self):self.reject(lambda:SafeCounter().add(-1))
    def test_backpressure(self):self.assertEqual(backpressure(12,5)["rejected"],7)
    def test_backpressure_none(self):self.assertEqual(backpressure(2,5)["rejected"],0)
    def test_backpressure_invalid(self):self.reject(lambda:backpressure(-1,5))
    def test_p50(self):self.assertEqual(percentile([1,2,3],50),2)
    def test_p95(self):self.assertAlmostEqual(percentile([0,100],95),95)
    def test_p99(self):self.assertAlmostEqual(percentile([0,100],99),99)
    def test_percentile_empty(self):self.reject(lambda:percentile([],50))
    def test_percentile_nan(self):self.reject(lambda:percentile([math.nan],50))
    def test_percentile_invalid(self):self.reject(lambda:percentile([1],101))
    def test_benchmark(self):self.assertEqual(benchmark(cpu_task,100,iterations=3)["iterations"],3)
    def test_benchmark_invalid(self):self.reject(lambda:benchmark(cpu_task,100,iterations=0))
    def test_incident_saturation(self):self.assertTrue(Incident("db",10,10,2,0.1).diagnose()["saturated"])
    def test_incident_queue(self):self.assertTrue(Incident("db",1,10,2,0).diagnose()["queued"])
    def test_incident_errors(self):self.assertTrue(Incident("db",1,10,0,0.05).diagnose()["error_budget_risk"])
    def test_incident_bad(self):self.reject(lambda:Incident("db",1,10,0,math.nan).diagnose())
    def test_incident_negative(self):self.reject(lambda:Incident("db",-1,10,0,0).diagnose())
    def test_no_writes(self):self.assertEqual(demo()["mutations"],0)
    def test_no_network(self):self.assertEqual(demo()["network_calls"],0)
    def test_cli(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(out.getvalue())["backpressure"]["rejected"],7)
if __name__=="__main__":unittest.main()
