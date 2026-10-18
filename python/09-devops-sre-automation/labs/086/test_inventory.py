"""Offline Kubernetes/Docker unit tests. No daemon, kubeconfig or credentials."""
import json
from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace as O
import unittest
from inventory import (
    InventoryError,Record,_namespace,deployment_ready,
    deployment_records,docker_records,fake_clients,limited,main,
    pod_records,watch_events
)

class InventoryTests(unittest.TestCase):
    def test_namespace(self):
        self.assertEqual(_namespace("db-prod"),"db-prod")
    def test_namespace_traversal(self):
        with self.assertRaises(ValueError): _namespace("../prod")
    def test_pod_pagination(self):
        core,_,_=fake_clients()
        records=list(pod_records(core,"db-prod"))
        self.assertEqual(len(records),2)
        self.assertTrue(records[0].healthy)
        self.assertFalse(records[1].healthy)
    def test_pod_bad_name(self):
        class Core:
            def list_namespaced_pod(self,**kwargs):
                return O(items=[O(metadata=O(name=None),status=O(phase="Running",conditions=[]))],
                         metadata=O(_continue=None))
        with self.assertRaises(InventoryError):
            list(pod_records(Core(),"default"))
    def test_pod_token_cycle(self):
        class Core:
            def list_namespaced_pod(self,**kwargs):
                return O(items=[],metadata=O(_continue="same"))
        with self.assertRaises(InventoryError):
            list(pod_records(Core(),"default"))
    def test_deployment_healthy(self):
        _,apps,_=fake_clients()
        records=list(deployment_records(apps,"default"))
        self.assertEqual(len(records),1)
        self.assertTrue(records[0].healthy)
    def test_deployment_observed_generation_lag(self):
        deployment=O(metadata=O(generation=3),spec=O(replicas=2),
                     status=O(observed_generation=2,updated_replicas=2,
                              ready_replicas=2,available_replicas=2))
        self.assertFalse(deployment_ready(deployment))
    def test_deployment_not_available(self):
        deployment=O(metadata=O(generation=1),spec=O(replicas=2),
                     status=O(observed_generation=1,updated_replicas=2,
                              ready_replicas=2,available_replicas=1))
        self.assertFalse(deployment_ready(deployment))
    def test_zero_replica_scaled_down(self):
        deployment=O(metadata=O(generation=1),spec=O(replicas=0),
                     status=O(observed_generation=1,updated_replicas=0,
                              ready_replicas=0,available_replicas=0))
        self.assertFalse(deployment_ready(deployment))
    def test_deployment_invalid_replica(self):
        deployment=O(metadata=O(generation=1),spec=O(replicas=-1),status=O())
        with self.assertRaises(InventoryError): deployment_ready(deployment)
    def test_docker_inventory(self):
        _,_,docker=fake_clients()
        self.assertTrue(list(docker_records(docker))[0].healthy)
    def test_docker_invalid_name(self):
        client=O(containers=O(list=lambda **kwargs:[O(name=None,status="running")]))
        with self.assertRaises(InventoryError):
            list(docker_records(client))
    def test_dedup(self):
        row=Record("kubernetes","default","pod","p",True,"Ready")
        self.assertEqual(len(limited([row,row],1)["records"]),1)
        self.assertFalse(limited([row,row],1)["partial"])
    def test_partial(self):
        rows=[Record("kubernetes","default","pod",str(i),True,"Ready") for i in range(3)]
        self.assertTrue(limited(rows,2)["partial"])
    def test_invalid_limit(self):
        with self.assertRaises(ValueError): limited([],0)
    def test_watch(self):
        self.assertEqual(watch_events([{"type":"ADDED"},{"type":"MODIFIED"}])["events"],
                         ["ADDED","MODIFIED"])
    def test_watch_partial(self):
        self.assertTrue(watch_events([{"type":"ADDED"},{"type":"DELETED"}],1)["partial"])
    def test_watch_unknown_event(self):
        with self.assertRaises(InventoryError): watch_events([{"type":"UNKNOWN"}])
    def test_dry_run(self):
        out=StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(["--namespace","db-prod","--dry-run"]),0)
        self.assertEqual(json.loads(out.getvalue())["network_calls"],0)
    def test_offline_cli(self):
        out=StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(["--namespace","db-prod","--max-records","2"]),0)
        payload=json.loads(out.getvalue())
        self.assertTrue(payload["partial"])
        self.assertEqual(len(payload["records"]),2)

if __name__=="__main__":
    unittest.main()
