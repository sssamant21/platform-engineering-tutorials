"""Offline deterministic SLI, burn-rate, error budget and readiness tests."""
import json,unittest
from contextlib import redirect_stdout
from io import StringIO
from reliability import Event,Objective,ReliabilityError,window,multiwindow_burn,readiness,REQUIRED_CHECKS,fake_events,main

class Tests(unittest.TestCase):
    def setUp(self):
        self.obj=Objective(target=.99,min_events=2)
        self.events=[Event(10,True,True,100),Event(11,False,True,700),
                     Event(12,True,False,10),Event(13,True,True,200)]
    def test_availability(self):self.assertAlmostEqual(window(self.events,0,20,self.obj)["availability"],2/3)
    def test_latency_sli(self):self.assertAlmostEqual(window(self.events,0,20,self.obj)["latency_sli"],2/3)
    def test_excluded_event(self):self.assertEqual(window(self.events,0,20,self.obj)["total"],3)
    def test_half_open_window(self):self.assertEqual(window(self.events,10,11,self.obj)["total"],1)
    def test_no_traffic(self):self.assertIsNone(window([],0,20,self.obj)["availability"])
    def test_no_traffic_unknown_burn(self):self.assertIsNone(window([],0,20,self.obj)["burn_rate"])
    def test_remaining_budget(self):self.assertLess(window(self.events,0,20,self.obj)["remaining_budget"],0)
    def test_budget_fraction(self):self.assertLess(window(self.events,0,20,self.obj)["budget_fraction"],0)
    def test_burn_rate(self):self.assertGreater(window(self.events,0,20,self.obj)["burn_rate"],30)
    def test_sufficient(self):self.assertTrue(window(self.events,0,20,self.obj)["sufficient"])
    def test_insufficient(self):self.assertFalse(window(self.events,10,11,self.obj)["sufficient"])
    def test_invalid_target(self):
        with self.assertRaises(ReliabilityError):window([],0,20,Objective(target=1))
    def test_invalid_latency(self):
        with self.assertRaises(ReliabilityError):window([],0,20,Objective(latency_threshold_ms=-1))
    def test_invalid_min_events(self):
        with self.assertRaises(ReliabilityError):window([],0,20,Objective(min_events=0))
    def test_invalid_window(self):
        with self.assertRaises(ReliabilityError):window([],10,10,self.obj)
    def test_invalid_event(self):
        with self.assertRaises(ReliabilityError):window([Event(10,True,True,-1)],0,20,self.obj)
    def test_invalid_classification(self):
        with self.assertRaises(ReliabilityError):window([Event(10,1,True,10)],0,20,self.obj)
    def test_fast_burn(self):
        result=multiwindow_burn(fake_events(failures=20),3600,self.obj,threshold=2)
        self.assertTrue(result["active"])
    def test_no_burn(self):
        self.assertFalse(multiwindow_burn(fake_events(failures=0),3600,self.obj,threshold=2)["active"])
    def test_missing_traffic_no_alert(self):
        self.assertFalse(multiwindow_burn([],3600,self.obj)["active"])
    def test_invalid_windows(self):
        with self.assertRaises(ReliabilityError):
            multiwindow_burn([],3600,self.obj,short_seconds=3600,long_seconds=300)
    def test_ready(self):
        burn=multiwindow_burn(fake_events(failures=0),3600,self.obj)
        self.assertTrue(readiness({k:True for k in REQUIRED_CHECKS},burn)["ready"])
    def test_missing_check(self):
        burn=multiwindow_burn(fake_events(failures=0),3600,self.obj)
        self.assertFalse(readiness({},burn)["ready"])
    def test_failed_backup(self):
        burn=multiwindow_burn(fake_events(failures=0),3600,self.obj)
        checks={k:True for k in REQUIRED_CHECKS};checks["backup_restore_tested"]=False
        self.assertIn("backup_restore_tested",readiness(checks,burn)["reasons"])
    def test_active_sev1(self):
        burn=multiwindow_burn(fake_events(failures=0),3600,self.obj)
        self.assertFalse(readiness({k:True for k in REQUIRED_CHECKS},burn,open_sev1=True)["ready"])
    def test_burn_blocks_release(self):
        burn=multiwindow_burn(fake_events(failures=20),3600,self.obj,threshold=2)
        self.assertIn("slo-fast-burn",readiness({k:True for k in REQUIRED_CHECKS},burn)["reasons"])
    def test_insufficient_samples_block_release(self):
        burn=multiwindow_burn([],3600,self.obj)
        self.assertIn("insufficient-sli-samples",readiness({k:True for k in REQUIRED_CHECKS},burn)["reasons"])
    def test_missing_burn_blocks_release(self):
        self.assertIn("missing-burn-evidence",readiness({k:True for k in REQUIRED_CHECKS},{})["reasons"])
    def test_fixture_invalid(self):
        with self.assertRaises(ReliabilityError):fake_events(failures=101)
    def test_cli_dry_run(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(out.getvalue())["mutations"],0)
    def test_cli_offline(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--failures","0"]),0)
        self.assertTrue(json.loads(out.getvalue())["release_gate"]["ready"])
    def test_cli_invalid_target(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--target","1"]),2)

if __name__=="__main__":unittest.main()
