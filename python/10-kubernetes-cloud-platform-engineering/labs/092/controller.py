"""Offline Kubernetes-style controller simulator. No network or real-cluster mutations."""
from __future__ import annotations
from dataclasses import dataclass,field
from collections import deque
import argparse,json,re,time

NAME=re.compile(r"^[a-z][a-z0-9-]{0,39}$")
FINALIZER="sre.example.io/databasecheck-cleanup"
class ControllerError(Exception):pass
class Conflict(ControllerError):pass
class Transient(ControllerError):pass

@dataclass
class CR:
    namespace:str
    name:str
    generation:int=1
    desired_healthy:bool=True
    observed_healthy:bool=False
    observed_generation:int=0
    resource_version:int=1
    finalizers:list[str]=field(default_factory=list)
    deleting:bool=False
    def validate(self):
        if not NAME.fullmatch(self.namespace) or not NAME.fullmatch(self.name):
            raise ControllerError("invalid namespace/name")
        if type(self.generation) is not int or self.generation<1:
            raise ControllerError("invalid generation")
        if type(self.desired_healthy) is not bool or type(self.observed_healthy) is not bool:
            raise ControllerError("invalid health")
        if type(self.resource_version) is not int or self.resource_version<1:
            raise ControllerError("invalid resourceVersion")

class FakeAPI:
    def __init__(self,objects:list[CR]):
        self.objects={}
        for obj in objects:
            obj.validate()
            key=(obj.namespace,obj.name)
            if key in self.objects:raise ControllerError("duplicate resource")
            self.objects[key]=obj
        self.reads=0
    def get(self,namespace,name):
        self.reads+=1
        return self.objects.get((namespace,name))
    def list(self,namespace):
        return [v for (ns,_),v in self.objects.items() if ns==namespace]

class Queue:
    def __init__(self,max_size=100):
        if not 1<=max_size<=10000:raise ValueError("invalid queue size")
        self.pending=deque();self.known=set();self.max_size=max_size
    def add(self,key):
        if not isinstance(key,tuple) or len(key)!=2 or not all(isinstance(x,str) and NAME.fullmatch(x) for x in key):
            raise ControllerError("invalid key")
        if key in self.known:return False
        if len(self.pending)>=self.max_size:raise ControllerError("queue full")
        self.pending.append(key);self.known.add(key);return True
    def pop(self):
        if not self.pending:return None
        key=self.pending.popleft();self.known.remove(key);return key
    def __len__(self):return len(self.pending)

@dataclass
class Lease:
    holder:str
    epoch:int=1
    expires_at:float=1000
    def allows(self,actor,epoch,now):
        return bool(self.holder==actor and self.epoch==epoch and now<self.expires_at)

def plan(obj:CR|None):
    if obj is None:return {"action":"forget","reason":"not-found"}
    obj.validate()
    if obj.deleting:
        return {"action":"hold-finalizer" if FINALIZER in obj.finalizers else "observe-deletion",
                "reason":"manual-cleanup-verification-required"}
    if FINALIZER not in obj.finalizers:
        return {"action":"propose-finalizer","reason":"owner-approval-required"}
    if obj.observed_generation!=obj.generation or obj.observed_healthy!=obj.desired_healthy:
        return {"action":"propose-status","reason":"drift-detected",
                "desiredHealthy":obj.desired_healthy,"observedGeneration":obj.generation}
    return {"action":"noop","reason":"converged"}

def reconcile(api:FakeAPI,key,*,dry_run=True,lease:Lease|None=None,
              actor="controller-a",epoch=1,now=100):
    if not dry_run and (lease is None or not lease.allows(actor,epoch,now)):
        raise ControllerError("leader fencing rejected")
    obj=api.get(*key)
    decision=plan(obj)
    # This educational implementation NEVER writes; non-dry-run only tests the fence.
    return {"key":"/".join(key),"dry_run":dry_run,"decision":decision,
            "mutations":0,"resourceVersion":obj.resource_version if obj else None}

def retry_read(fn,*,attempts=3,delay=lambda seconds:None):
    if not 1<=attempts<=8:raise ValueError("invalid retries")
    for i in range(attempts):
        try:return fn()
        except Transient:
            if i==attempts-1:raise
            delay(min(2**i,8))
    raise AssertionError("unreachable")

def watch_to_queue(events,queue:Queue,*,max_events=100):
    if not 1<=max_events<=10000:raise ValueError("invalid event budget")
    for index,event in enumerate(events):
        if index>=max_events:raise ControllerError("watch budget exceeded")
        typ=event.get("type")
        if typ=="ERROR":
            if event.get("code")==410:raise ControllerError("resourceVersion expired; relist")
            raise ControllerError("watch error")
        if typ=="BOOKMARK":continue
        if typ not in ("ADDED","MODIFIED","DELETED"):raise ControllerError("invalid event")
        queue.add((event.get("namespace"),event.get("name")))
    return len(queue)

def relist(api,namespace,queue):
    for obj in api.list(namespace):queue.add((obj.namespace,obj.name))
    return len(queue)

def run_queue(api,queue,*,budget=100):
    if not 1<=budget<=10000:raise ValueError("invalid reconcile budget")
    results=[]
    while len(queue):
        if len(results)>=budget:raise ControllerError("reconcile budget exceeded")
        key=queue.pop()
        results.append(reconcile(api,key))
    return results

def demo():
    obj=CR("sre-lab","postgres-check",desired_healthy=True,observed_healthy=False,
           finalizers=[FINALIZER])
    api=FakeAPI([obj]);queue=Queue()
    watch_to_queue([{"type":"ADDED","namespace":"sre-lab","name":"postgres-check"},
                    {"type":"MODIFIED","namespace":"sre-lab","name":"postgres-check"}],queue)
    return {"mode":"offline-fake","results":run_queue(api,queue),
            "api_reads":api.reads,"network_calls":0,"mutations":0}

def main(argv=None):
    parser=argparse.ArgumentParser(description="Offline Kubernetes controller capstone")
    parser.add_argument("--dry-run",action="store_true")
    args=parser.parse_args(argv)
    print(json.dumps(demo(),sort_keys=True))
    return 0

if __name__=="__main__":raise SystemExit(main())
