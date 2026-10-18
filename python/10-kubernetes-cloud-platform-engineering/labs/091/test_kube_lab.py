import json,unittest
from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace as N
from kube_lab import (LabError,Meta,Container,PodStatus,Pod,Page,FakeCore,retry_read,
                      pages,pod_summary,deployment_health,consume_watch,demo,main)
class ApiError(Exception):
    def __init__(self,status):self.status=status
class Tests(unittest.TestCase):
    def setUp(self):
        self.pods=[Pod(Meta("p1"),PodStatus("Running",[Container(True)])),
                   Pod(Meta("p2"),PodStatus("Pending",[Container(False)]))]
    def test_pages(self):self.assertEqual(len(pages(FakeCore(self.pods).list_namespaced_pod,"sre-lab",limit=1)),2)
    def test_page_count(self):
        c=FakeCore(self.pods);pages(c.list_namespaced_pod,"sre-lab",limit=1);self.assertEqual(c.calls,2)
    def test_empty(self):self.assertEqual(pages(FakeCore([]).list_namespaced_pod,"sre-lab"),[])
    def test_bad_namespace(self):
        with self.assertRaises(ValueError):pages(FakeCore([]).list_namespaced_pod,"../prod")
    def test_bad_limit(self):
        with self.assertRaises(ValueError):pages(FakeCore([]).list_namespaced_pod,"sre-lab",limit=0)
    def test_object_budget(self):
        with self.assertRaises(LabError):pages(FakeCore(self.pods).list_namespaced_pod,"sre-lab",max_items=1)
    def test_page_budget(self):
        with self.assertRaises(LabError):pages(FakeCore(self.pods).list_namespaced_pod,"sre-lab",limit=1,max_pages=1)
    def test_token_loop(self):
        def fetch(**kwargs):return Page([],Meta(_continue="same"))
        with self.assertRaises(LabError):pages(fetch,"sre-lab")
    def test_transient_retry(self):
        calls=[0]
        def f():
            calls[0]+=1
            if calls[0]==1:raise ApiError(429)
            return 7
        self.assertEqual(retry_read(f,delay=lambda s:None),7)
    def test_nonretry_403(self):
        def f():raise ApiError(403)
        with self.assertRaises(ApiError):retry_read(f,delay=lambda s:None)
    def test_retry_exhausted(self):
        def f():raise ApiError(503)
        with self.assertRaises(ApiError):retry_read(f,attempts=2,delay=lambda s:None)
    def test_retry_bad_attempts(self):
        with self.assertRaises(ValueError):retry_read(lambda:1,attempts=0)
    def test_pod_summary(self):self.assertEqual(pod_summary(self.pods)["not_ready"],["p2"])
    def test_pod_phases(self):self.assertEqual(pod_summary(self.pods)["phases"]["Pending"],1)
    def test_missing_containers(self):
        self.assertEqual(pod_summary([Pod(Meta("p"),PodStatus("Running",[]))])["not_ready"],["p"])
    def test_duplicate_pod(self):
        with self.assertRaises(LabError):pod_summary([self.pods[0],self.pods[0]])
    def test_invalid_pod(self):
        with self.assertRaises(LabError):pod_summary([Pod(Meta(""),PodStatus("Running",[]))])
    def deployment(self,desired=2,updated=2,available=2,observed=3):
        return N(metadata=N(generation=3),spec=N(replicas=desired),
                 status=N(updated_replicas=updated,available_replicas=available,observed_generation=observed))
    def test_rollout_healthy(self):self.assertTrue(deployment_health(self.deployment())["healthy"])
    def test_rollout_pending(self):self.assertFalse(deployment_health(self.deployment(observed=2))["healthy"])
    def test_rollout_unavailable(self):self.assertFalse(deployment_health(self.deployment(available=1))["healthy"])
    def test_bad_deployment(self):
        with self.assertRaises(LabError):deployment_health(self.deployment(desired=-1))
    def test_watch_add(self):
        r=consume_watch([{"type":"ADDED","object":{"name":"p","resourceVersion":"1"}}])
        self.assertEqual(r["objects"]["p"],"1")
    def test_watch_delete(self):
        r=consume_watch([{"type":"ADDED","object":{"name":"p","resourceVersion":"1"}},
                         {"type":"DELETED","object":{"name":"p","resourceVersion":"2"}}])
        self.assertEqual(r["objects"],{})
    def test_watch_bookmark(self):
        self.assertEqual(consume_watch([{"type":"BOOKMARK","resourceVersion":"10"}])["resourceVersion"],"10")
    def test_watch_expired(self):
        with self.assertRaises(LabError):consume_watch([{"type":"ERROR","code":410}])
    def test_watch_unknown(self):
        with self.assertRaises(LabError):consume_watch([{"type":"UNKNOWN"}])
    def test_watch_budget(self):
        with self.assertRaises(LabError):consume_watch([{"type":"BOOKMARK"}]*2,max_events=1)
    def test_watch_bad_object(self):
        with self.assertRaises(LabError):consume_watch([{"type":"ADDED","object":{"name":"p"}}])
    def test_demo(self):self.assertEqual(demo()["mutations"],0)
    def test_cli_dry_run(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(out.getvalue())["network_calls"],0)
    def test_cli_offline(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main([]),0)
        self.assertEqual(json.loads(out.getvalue())["inventory"]["total"],2)
if __name__=="__main__":unittest.main()
