import json,unittest
from io import StringIO
from contextlib import redirect_stdout
from platform_lab import PlatformError,Event,authorized,Pipeline,capacity,slo,dr,acceptance,demo,main
class Tests(unittest.TestCase):
    def bad(self,fn):
        with self.assertRaises(PlatformError):fn()
    def event(self,version=1):return Event("record",version,"synthetic","tenant-a")
    def test_event(self):self.assertEqual(self.event().version,1)
    def test_event_digest(self):self.assertEqual(self.event().digest,self.event().digest)
    def test_event_bad_key(self):self.bad(lambda:Event("",1,"x","t"))
    def test_event_bad_version(self):self.bad(lambda:Event("x",0,"x","t"))
    def test_event_bad_tenant(self):self.bad(lambda:Event("x",1,"x",""))
    def test_event_bad_payload(self):self.bad(lambda:Event("x",1,"x"*4097,"t"))
    def test_writer_authorized(self):self.assertTrue(authorized("writer","tenant-a",self.event()))
    def test_tenant_denied(self):self.assertFalse(authorized("writer","tenant-b",self.event()))
    def test_reader_denied(self):self.assertFalse(authorized("reader","tenant-a",self.event()))
    def test_admin(self):self.assertTrue(authorized("admin","other",self.event()))
    def test_pipeline_empty(self):self.assertTrue(Pipeline().reconcile()["consistent"])
    def test_submit(self):self.assertTrue(Pipeline().submit(self.event()))
    def test_cross_tenant(self):self.assertFalse(Pipeline().submit(self.event(),principal_tenant="tenant-b"))
    def test_source_revision(self):
        p=Pipeline();self.assertTrue(p.submit(self.event()));self.assertTrue(p.submit(self.event(2)));self.assertEqual(p.source[("tenant-a","record")].version,2)
    def test_stale(self):
        p=Pipeline();p.submit(self.event());self.assertFalse(p.submit(self.event()));self.assertEqual(p.metrics["stale"],1)
    def test_backpressure(self):
        p=Pipeline(queue_limit=1);p.submit(self.event());self.assertFalse(p.submit(Event("another",1,"x","tenant-a")))
    def test_publish(self):
        p=Pipeline();p.submit(self.event());self.assertEqual(p.publish(),1)
    def test_publish_batch(self):
        p=Pipeline();p.submit(self.event());self.assertEqual(p.publish(1),1)
    def test_publish_invalid(self):self.bad(lambda:Pipeline().publish(0))
    def test_partition_stable(self):
        p=Pipeline();p.submit(self.event());p.publish();self.assertEqual(sum(map(len,p.log)),1)
    def test_consume(self):
        p=Pipeline();p.submit(self.event());p.publish();self.assertEqual(p.consume(),1)
    def test_idempotent_projection(self):
        p=Pipeline();p.submit(self.event());p.publish();p.consume();p.log[0].append(self.event()) if p.log[0] else p.log[next(i for i,v in enumerate(p.log) if v)].append(self.event());p.consume();self.assertEqual(p.metrics["applied"],1)
    def test_failed_sink_no_commit(self):
        p=Pipeline();p.submit(self.event());p.publish();self.assertEqual(p.consume(fail_keys={"record"}),0);self.assertEqual(sum(p.offsets),0)
    def test_lag(self):
        p=Pipeline();p.submit(self.event());self.assertEqual(p.lag(),1)
    def test_reconcile_missing(self):
        p=Pipeline();p.submit(self.event());self.assertFalse(p.reconcile()["consistent"])
    def test_reconcile_clean(self):
        p=Pipeline();p.submit(self.event());p.publish();p.consume();self.assertTrue(p.reconcile()["consistent"])
    def test_reconcile_version(self):
        p=Pipeline();p.submit(self.event());p.publish();p.consume();p.submit(self.event(2));self.assertFalse(p.reconcile()["consistent"])
    def test_reconcile_extra(self):
        p=Pipeline();p.search[("tenant-a","record")]=self.event();self.assertTrue(p.reconcile()["extra"])
    def test_invalid_partitions(self):self.bad(lambda:Pipeline(partitions=0))
    def test_invalid_queue(self):self.bad(lambda:Pipeline(queue_limit=0))
    def test_capacity(self):self.assertFalse(capacity(200,4)["saturated"])
    def test_capacity_overload(self):self.assertTrue(capacity(2000,4)["saturated"])
    def test_capacity_bad(self):self.bad(lambda:capacity(-1,4))
    def test_slo_pass(self):self.assertEqual(slo(1000,1000)["status"],"pass")
    def test_slo_breach(self):self.assertEqual(slo(900,1000)["status"],"breach")
    def test_slo_unknown(self):self.assertEqual(slo(0,0)["status"],"unknown")
    def test_slo_invalid(self):self.bad(lambda:slo(11,10))
    def test_dr_ready(self):self.assertEqual(dr(10,60,30,60,True,True,True)["decision"],"advisory-ready")
    def test_dr_rpo(self):self.assertIn("rpo",dr(100,60,30,60,True,True,True)["blockers"])
    def test_dr_rto(self):self.assertIn("rto",dr(10,60,90,60,True,True,True)["blockers"])
    def test_dr_fencing(self):self.assertIn("fencing",dr(10,60,30,60,False,True,True)["blockers"])
    def test_dr_approval(self):self.assertIn("approval",dr(10,60,30,60,True,False,True)["blockers"])
    def test_dr_verification(self):self.assertIn("verification",dr(10,60,30,60,True,True,False)["blockers"])
    def test_accept_ready(self):self.assertEqual(acceptance(True,0,True,True,True,True,True,True,True,True)["score"],100)
    def test_accept_lag(self):self.assertEqual(acceptance(True,1,True,True,True,True,True,True,True,True)["decision"],"hold")
    def test_accept_security(self):self.assertIn("security",acceptance(True,0,True,True,True,False,True,True,True,True)["failed"])
    def test_accept_no_approval(self):self.assertEqual(acceptance(True,0,True,True,True,True,True,True,True,False)["decision"],"hold")
    def test_accept_bad(self):self.bad(lambda:acceptance(True,-1,True,True,True,True,True,True,True,True))
    def test_demo_ready(self):self.assertEqual(demo()["acceptance"]["decision"],"advisory-ready")
    def test_demo_failure(self):self.assertEqual(demo(True)["acceptance"]["decision"],"hold")
    def test_demo_no_network(self):self.assertEqual(demo()["network_calls"],0)
    def test_demo_no_mutations(self):self.assertEqual(demo()["production_changes"],0)
    def test_fingerprint(self):self.assertNotEqual(demo()["fingerprint"],demo(True)["fingerprint"])
    def test_cli(self):
        output=StringIO()
        with redirect_stdout(output):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(output.getvalue())["mode"],"offline")
if __name__=="__main__":unittest.main()
