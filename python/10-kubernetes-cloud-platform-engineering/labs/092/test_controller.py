"""Deterministic tests for the Chapter 092 controller simulator."""
import json,unittest
from contextlib import redirect_stdout
from io import StringIO
from controller import (CR,FINALIZER,FakeAPI,Queue,Lease,ControllerError,Transient,
                        plan,reconcile,retry_read,watch_to_queue,relist,run_queue,demo,main)
class Tests(unittest.TestCase):
    def setUp(self):
        self.obj=CR("sre-lab","postgres-check",finalizers=[FINALIZER])
        self.api=FakeAPI([self.obj])
    def test_valid(self):self.obj.validate()
    def test_invalid_name(self):
        with self.assertRaises(ControllerError):CR("../prod","db").validate()
    def test_invalid_generation(self):
        with self.assertRaises(ControllerError):CR("sre-lab","db",generation=0).validate()
    def test_invalid_health(self):
        with self.assertRaises(ControllerError):CR("sre-lab","db",desired_healthy=1).validate()
    def test_duplicate_resource(self):
        with self.assertRaises(ControllerError):FakeAPI([self.obj,self.obj])
    def test_get(self):self.assertIs(self.api.get("sre-lab","postgres-check"),self.obj)
    def test_list(self):self.assertEqual(len(self.api.list("sre-lab")),1)
    def test_missing(self):self.assertEqual(plan(None)["action"],"forget")
    def test_finalizer_plan(self):self.assertEqual(plan(CR("sre-lab","db"))["action"],"propose-finalizer")
    def test_status_plan(self):self.assertEqual(plan(self.obj)["action"],"propose-status")
    def test_converged(self):
        self.obj.observed_healthy=True
        self.obj.observed_generation=1
        self.assertEqual(plan(self.obj)["action"],"noop")
    def test_delete_hold(self):
        self.obj.deleting=True
        self.assertEqual(plan(self.obj)["action"],"hold-finalizer")
    def test_delete_no_finalizer(self):
        self.obj.deleting=True;self.obj.finalizers=[]
        self.assertEqual(plan(self.obj)["action"],"observe-deletion")
    def test_reconcile_read_only(self):
        result=reconcile(self.api,("sre-lab","postgres-check"))
        self.assertEqual(result["mutations"],0)
    def test_lease_good(self):self.assertTrue(Lease("worker",2,1000).allows("worker",2,500))
    def test_lease_stale(self):self.assertFalse(Lease("worker",2,1000).allows("worker",1,500))
    def test_lease_expired(self):self.assertFalse(Lease("worker",2,1000).allows("worker",2,1000))
    def test_fenced_apply(self):
        with self.assertRaises(ControllerError):
            reconcile(self.api,("sre-lab","postgres-check"),dry_run=False)
    def test_lease_allows_noop(self):
        result=reconcile(self.api,("sre-lab","postgres-check"),dry_run=False,
                         lease=Lease("controller-a",1,1000))
        self.assertEqual(result["mutations"],0)
    def test_queue_dedup(self):
        q=Queue();self.assertTrue(q.add(("sre-lab","db")))
        self.assertFalse(q.add(("sre-lab","db")))
        self.assertEqual(len(q),1)
    def test_queue_pop(self):
        q=Queue();q.add(("sre-lab","db"))
        self.assertEqual(q.pop(),("sre-lab","db"))
        self.assertIsNone(q.pop())
    def test_queue_limit(self):
        q=Queue(1);q.add(("sre-lab","a"))
        with self.assertRaises(ControllerError):q.add(("sre-lab","b"))
    def test_bad_queue_key(self):
        with self.assertRaises(ControllerError):Queue().add(("../x","db"))
    def test_watch_add(self):
        q=Queue()
        self.assertEqual(watch_to_queue([{"type":"ADDED","namespace":"sre-lab","name":"db"}],q),1)
    def test_watch_duplicate(self):
        q=Queue()
        watch_to_queue([{"type":"ADDED","namespace":"sre-lab","name":"db"},
                        {"type":"MODIFIED","namespace":"sre-lab","name":"db"}],q)
        self.assertEqual(len(q),1)
    def test_watch_bookmark(self):self.assertEqual(watch_to_queue([{"type":"BOOKMARK"}],Queue()),0)
    def test_watch_expired(self):
        with self.assertRaisesRegex(ControllerError,"relist"):
            watch_to_queue([{"type":"ERROR","code":410}],Queue())
    def test_watch_unknown(self):
        with self.assertRaises(ControllerError):watch_to_queue([{"type":"INVALID"}],Queue())
    def test_watch_budget(self):
        with self.assertRaises(ControllerError):
            watch_to_queue([{"type":"BOOKMARK"},{"type":"BOOKMARK"}],Queue(),max_events=1)
    def test_relist(self):
        q=Queue();self.assertEqual(relist(self.api,"sre-lab",q),1)
    def test_run_queue(self):
        q=Queue();relist(self.api,"sre-lab",q)
        self.assertEqual(len(run_queue(self.api,q)),1)
    def test_reconcile_budget(self):
        q=Queue();q.add(("sre-lab","a"));q.add(("sre-lab","b"))
        with self.assertRaises(ControllerError):run_queue(self.api,q,budget=1)
    def test_retry_transient(self):
        calls=[0]
        def f():
            calls[0]+=1
            if calls[0]==1:raise Transient()
            return "ok"
        self.assertEqual(retry_read(f),"ok")
    def test_retry_exhausted(self):
        def f():raise Transient()
        with self.assertRaises(Transient):retry_read(f,attempts=2)
    def test_retry_invalid(self):
        with self.assertRaises(ValueError):retry_read(lambda:1,attempts=0)
    def test_demo(self):self.assertEqual(demo()["mutations"],0)
    def test_cli(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(out.getvalue())["network_calls"],0)
if __name__=="__main__":unittest.main()
