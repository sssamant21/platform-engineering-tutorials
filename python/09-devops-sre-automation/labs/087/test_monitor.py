import json,unittest
from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace as O
from monitor import Sample,Sampler,Rule,Alerts,SLO,prometheus_text,main
class Tests(unittest.TestCase):
    def sample(self,cpu,at=0):return Sample(cpu,10,20,at)
    def test_valid(self):self.sample(20).validate()
    def test_nan(self):
        with self.assertRaises(ValueError):self.sample(float("nan")).validate()
    def test_negative(self):
        with self.assertRaises(ValueError):self.sample(-1).validate()
    def test_over_100(self):
        with self.assertRaises(ValueError):self.sample(101).validate()
    def test_timestamp(self):
        with self.assertRaises(ValueError):self.sample(1,float("inf")).validate()
    def test_sampler(self):
        p=O(cpu_percent=lambda interval:12,virtual_memory=lambda:O(percent=34),disk_usage=lambda path:O(percent=56))
        self.assertEqual(Sampler(p).sample(clock=lambda:123).memory,34)
    def test_warning(self):self.assertEqual(Alerts({"cpu":Rule()}).evaluate(self.sample(80))[0]["severity"],"warning")
    def test_critical(self):self.assertEqual(Alerts({"cpu":Rule()}).evaluate(self.sample(95))[0]["severity"],"critical")
    def test_ok(self):self.assertEqual(Alerts({"cpu":Rule()}).evaluate(self.sample(50)),[])
    def test_dedup(self):
        a=Alerts({"cpu":Rule()});a.evaluate(self.sample(80));self.assertEqual(a.evaluate(self.sample(80,1)),[])
    def test_cooldown(self):
        a=Alerts({"cpu":Rule()},30);a.evaluate(self.sample(80));self.assertEqual(a.evaluate(self.sample(80,30))[0]["transition"],"repeat")
    def test_hysteresis(self):
        a=Alerts({"cpu":Rule()});a.evaluate(self.sample(95));self.assertEqual(a.evaluate(self.sample(72,1)),[])
        self.assertEqual(a.evaluate(self.sample(69,2))[0]["severity"],"ok")
    def test_escalation(self):
        a=Alerts({"cpu":Rule()});a.evaluate(self.sample(80));self.assertEqual(a.evaluate(self.sample(95,1))[0]["severity"],"critical")
    def test_bad_rule(self):
        with self.assertRaises(ValueError):Alerts({"cpu":Rule(90,80,70)})
    def test_bad_cooldown(self):
        with self.assertRaises(ValueError):Alerts(cooldown=-1)
    def test_prometheus(self):self.assertIn("sre_host_cpu_usage_percent 50",prometheus_text(self.sample(50)))
    def test_slo_empty(self):self.assertIsNone(SLO().availability())
    def test_slo_ratio(self):
        s=SLO();s.observe(True);s.observe(False);self.assertEqual(s.availability(),.5)
    def test_slo_budget(self):
        s=SLO();[s.observe(True) for _ in range(100)];self.assertAlmostEqual(s.budget(.99),1)
    def test_slo_exhausted(self):
        s=SLO();[s.observe(True) for _ in range(99)];s.observe(False);s.observe(False);self.assertLess(s.budget(.99),0)
    def test_slo_type(self):
        with self.assertRaises(TypeError):SLO().observe("ok")
    def test_slo_target(self):
        with self.assertRaises(ValueError):SLO().budget(1)
    def test_slo_window(self):
        s=SLO(2);s.observe(True);s.observe(True);s.observe(False);self.assertEqual(s.availability(),.5)
    def test_dry_run(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(out.getvalue())["sampling_calls"],0)
if __name__=="__main__":unittest.main()
