"""Read-only Kubernetes and Docker inventory; all SDK clients injected."""
from __future__ import annotations
import argparse
from dataclasses import asdict, dataclass
import json
from typing import Any, Iterable

class InventoryError(RuntimeError): pass

@dataclass(frozen=True)
class Record:
    source: str
    scope: str
    kind: str
    name: str
    healthy: bool
    reason: str

def limited(records: Iterable[Record], max_records: int) -> dict:
    if type(max_records) is not int or not 1 <= max_records <= 1000:
        raise ValueError("max_records must be 1..1000")
    rows=[]
    seen=set()
    for record in records:
        key=(record.source,record.scope,record.kind,record.name)
        if key in seen: continue
        seen.add(key)
        if len(rows)==max_records:
            return {"records":[asdict(r) for r in rows],"partial":True}
        rows.append(record)
    return {"records":[asdict(r) for r in rows],"partial":False}

def _namespace(namespace: str) -> str:
    if not namespace or len(namespace)>63 or not namespace[0].isalnum() or not namespace[-1].isalnum():
        raise ValueError("invalid namespace")
    if any(not(c.islower() or c.isdigit() or c=="-") for c in namespace):
        raise ValueError("invalid namespace")
    return namespace

def pod_records(core: Any, namespace: str, *, page_size: int=100) -> Iterable[Record]:
    namespace=_namespace(namespace)
    if not 1 <= page_size <= 500:
        raise ValueError("invalid page size")
    token=None
    seen_tokens=set()
    while True:
        page=core.list_namespaced_pod(namespace=namespace,limit=page_size,_continue=token,
                                      _request_timeout=10)
        for pod in page.items:
            name=getattr(pod.metadata,"name",None)
            if not isinstance(name,str) or not name:
                raise InventoryError("invalid pod name")
            phase=getattr(pod.status,"phase","Unknown")
            conditions=getattr(pod.status,"conditions",None) or []
            ready=any(getattr(c,"type",None)=="Ready" and getattr(c,"status",None)=="True"
                      for c in conditions)
            yield Record("kubernetes",namespace,"pod",name,ready,
                         "Ready" if ready else str(phase or "Unknown"))
        token=getattr(page.metadata,"_continue",None) or None
        if not token: break
        if token in seen_tokens:
            raise InventoryError("pagination token repeated")
        seen_tokens.add(token)

def deployment_ready(deployment: Any) -> bool:
    metadata=deployment.metadata
    spec=deployment.spec
    status=deployment.status
    generation=getattr(metadata,"generation",0) or 0
    observed=getattr(status,"observed_generation",0) or 0
    desired=getattr(spec,"replicas",None)
    if desired is None: desired=1
    if type(desired) is not int or desired < 0:
        raise InventoryError("invalid replica count")
    return (desired>0 and observed>=generation
            and (getattr(status,"updated_replicas",0) or 0)>=desired
            and (getattr(status,"available_replicas",0) or 0)>=desired
            and (getattr(status,"ready_replicas",0) or 0)>=desired)

def deployment_records(apps: Any, namespace: str, *, page_size: int=100) -> Iterable[Record]:
    namespace=_namespace(namespace)
    if not 1 <= page_size <= 500:
        raise ValueError("invalid page size")
    token=None
    seen_tokens=set()
    while True:
        page=apps.list_namespaced_deployment(namespace=namespace,limit=page_size,
                                             _continue=token,_request_timeout=10)
        for deployment in page.items:
            name=getattr(deployment.metadata,"name",None)
            if not isinstance(name,str) or not name:
                raise InventoryError("invalid deployment name")
            healthy=deployment_ready(deployment)
            yield Record("kubernetes",namespace,"deployment",name,healthy,
                         "available" if healthy else "rollout-pending-or-scaled-down")
        token=getattr(page.metadata,"_continue",None) or None
        if not token: break
        if token in seen_tokens:
            raise InventoryError("pagination token repeated")
        seen_tokens.add(token)

def docker_records(client: Any) -> Iterable[Record]:
    for container in client.containers.list(all=True):
        name=getattr(container,"name",None)
        status=getattr(container,"status","unknown")
        if not isinstance(name,str) or not name:
            raise InventoryError("invalid container name")
        yield Record("docker","local-daemon","container",name,
                     status=="running",str(status))

def watch_events(stream: Iterable[dict], max_events: int=100) -> dict:
    """Bound an already-established watch iterator; caller handles reconnect/410."""
    if type(max_events) is not int or not 1<=max_events<=1000:
        raise ValueError("invalid max_events")
    events=[]
    for event in stream:
        kind=event.get("type")
        if kind not in ("ADDED","MODIFIED","DELETED","BOOKMARK"):
            raise InventoryError("unexpected watch event")
        if len(events)==max_events:
            return {"events":events,"partial":True}
        events.append(kind)
    return {"events":events,"partial":False}

def fake_clients():
    """Deterministic offline SDK-shaped objects, no third-party imports."""
    from types import SimpleNamespace as O
    class Core:
        def list_namespaced_pod(self,**kwargs):
            if kwargs.get("_continue"):
                return O(items=[O(metadata=O(name="pod-b"),
                                  status=O(phase="Pending",conditions=[]))],
                         metadata=O(_continue=None))
            return O(items=[O(metadata=O(name="pod-a"),
                              status=O(phase="Running",
                                       conditions=[O(type="Ready",status="True")]))],
                     metadata=O(_continue="page-2"))
    class Apps:
        def list_namespaced_deployment(self,**kwargs):
            return O(items=[O(metadata=O(name="web",generation=2),
                              spec=O(replicas=2),
                              status=O(observed_generation=2,updated_replicas=2,
                                       ready_replicas=2,available_replicas=2))],
                     metadata=O(_continue=None))
    class Docker:
        containers=O(list=lambda **kwargs:[O(name="lab-container",status="running")])
    return Core(),Apps(),Docker()

def main(argv=None):
    parser=argparse.ArgumentParser(description="Offline Kubernetes and Docker inventory")
    parser.add_argument("--namespace",default="default")
    parser.add_argument("--max-records",type=int,default=100)
    parser.add_argument("--dry-run",action="store_true")
    args=parser.parse_args(argv)
    _namespace(args.namespace)
    if not 1<=args.max_records<=1000:
        parser.error("max-records must be 1..1000")
    if args.dry_run:
        print(json.dumps({"dry_run":True,"network_calls":0,"namespace":args.namespace}))
        return 0
    core,apps,docker=fake_clients()
    rows=limited((*pod_records(core,args.namespace),
                  *deployment_records(apps,args.namespace),
                  *docker_records(docker)),args.max_records)
    print(json.dumps({"mode":"offline-fake",**rows},sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
