"""Read-only Kubernetes inventory and rollout diagnostics; offline fakes by default."""
from __future__ import annotations
import argparse,json,math,time
from dataclasses import dataclass
from typing import Any,Callable

class LabError(Exception):pass

TRANSIENT={429,500,502,503,504}

def retry_read(fn:Callable[[],Any],*,attempts:int=3,delay:Callable[[float],None]=time.sleep)->Any:
    if not 1<=attempts<=8:raise ValueError("attempts out of range")
    for i in range(attempts):
        try:return fn()
        except Exception as exc:
            status=getattr(exc,"status",None)
            if status not in TRANSIENT or i==attempts-1:raise
            delay(min(2**i,8))
    raise AssertionError("unreachable")

def pages(fetch:Callable[...,Any],namespace:str,*,limit:int=50,max_pages:int=20,max_items:int=1000)->list:
    if not namespace or "/" in namespace or not 1<=limit<=500 or not 1<=max_pages<=100 or not 1<=max_items<=10000:
        raise ValueError("invalid inventory scope/budget")
    token=None;seen=set();result=[]
    for _ in range(max_pages):
        response=retry_read(lambda:fetch(namespace=namespace,limit=limit,_continue=token))
        result.extend(response.items)
        if len(result)>max_items:raise LabError("object budget exceeded")
        next_token=getattr(response.metadata,"_continue",None) or None
        if not next_token:return result
        if next_token in seen:raise LabError("pagination token loop")
        seen.add(next_token);token=next_token
    raise LabError("page budget exceeded")

def pod_summary(pods:list)->dict:
    names=set();phases={};not_ready=[]
    for pod in pods:
        meta=getattr(pod,"metadata",None)
        status=getattr(pod,"status",None)
        name=getattr(meta,"name",None)
        if not isinstance(name,str) or not name or name in names:raise LabError("invalid/duplicate pod")
        names.add(name)
        phase=getattr(status,"phase",None) or "Unknown"
        phases[phase]=phases.get(phase,0)+1
        containers=getattr(status,"container_statuses",None) or []
        if phase!="Running" or not containers or not all(getattr(c,"ready",False) is True for c in containers):
            not_ready.append(name)
    return {"total":len(pods),"phases":phases,"not_ready":sorted(not_ready)}

def deployment_health(deployment)->dict:
    spec=getattr(deployment,"spec",None);status=getattr(deployment,"status",None)
    meta=getattr(deployment,"metadata",None)
    desired=getattr(spec,"replicas",None)
    observed=getattr(status,"observed_generation",None)
    generation=getattr(meta,"generation",None)
    updated=getattr(status,"updated_replicas",None) or 0
    available=getattr(status,"available_replicas",None) or 0
    if not isinstance(desired,int) or desired<0 or not isinstance(generation,int) or generation<1:
        raise LabError("invalid deployment")
    healthy=(observed is not None and observed>=generation and updated>=desired and available>=desired)
    return {"desired":desired,"updated":updated,"available":available,
            "generation":generation,"observed_generation":observed,"healthy":healthy}

def consume_watch(events:list,*,max_events:int=100)->dict:
    if not 1<=max_events<=10000:raise ValueError("invalid watch budget")
    state={};last_rv=None
    for i,event in enumerate(events):
        if i>=max_events:raise LabError("watch event budget exceeded")
        typ=event.get("type")
        if typ=="ERROR":
            code=event.get("code")
            if code==410:raise LabError("resourceVersion expired; relist required")
            raise LabError("watch error")
        if typ=="BOOKMARK":
            last_rv=event.get("resourceVersion",last_rv);continue
        if typ not in ("ADDED","MODIFIED","DELETED"):raise LabError("unexpected watch event")
        obj=event.get("object") or {}
        name=obj.get("name");rv=obj.get("resourceVersion")
        if not isinstance(name,str) or not name or not isinstance(rv,str) or not rv:
            raise LabError("invalid watch object")
        if typ=="DELETED":state.pop(name,None)
        else:state[name]=rv
        last_rv=rv
    return {"objects":state,"resourceVersion":last_rv}

@dataclass
class Meta:
    name:str=""
    generation:int=1
    _continue:str=""

@dataclass
class Container:
    ready:bool=True

@dataclass
class PodStatus:
    phase:str="Running"
    container_statuses:list|None=None

@dataclass
class Pod:
    metadata:Meta
    status:PodStatus

@dataclass
class Page:
    items:list
    metadata:Meta

class FakeCore:
    def __init__(self,pods:list):self.pods=pods;self.calls=0
    def list_namespaced_pod(self,namespace,limit,_continue=None):
        if namespace!="sre-lab":raise LabError("namespace not found")
        self.calls+=1
        offset=int(_continue or 0)
        batch=self.pods[offset:offset+limit]
        nxt=str(offset+limit) if offset+limit<len(self.pods) else ""
        return Page(batch,Meta(_continue=nxt))

def demo():
    pods=[Pod(Meta("api-0"),PodStatus("Running",[Container(True)])),
          Pod(Meta("db-0"),PodStatus("Pending",[Container(False)]))]
    core=FakeCore(pods)
    return {"mode":"offline-fake","namespace":"sre-lab",
            "inventory":pod_summary(pages(core.list_namespaced_pod,"sre-lab",limit=1)),
            "pages_fetched":core.calls,"network_calls":0,"mutations":0}

def live_inventory(context,namespace,limit=50):
    """Optional read-only live Kubernetes inventory; no write methods are invoked."""
    if not context or not namespace or "/" in namespace:raise ValueError("explicit context/namespace required")
    from kubernetes import client,config
    config.load_kube_config(context=context)
    core=client.CoreV1Api()
    result=pages(core.list_namespaced_pod,namespace,limit=limit)
    return {"mode":"live-read-only","context":context,"namespace":namespace,
            "inventory":pod_summary(result),"mutations":0}

def main(argv=None):
    p=argparse.ArgumentParser(description="Kubernetes read-only inventory lab")
    p.add_argument("--dry-run",action="store_true")
    p.add_argument("--live",action="store_true")
    p.add_argument("--context")
    p.add_argument("--namespace")
    args=p.parse_args(argv)
    if args.live and (not args.context or not args.namespace):
        p.error("--live requires --context and --namespace")
    if args.dry_run:
        print(json.dumps({"mode":"dry-run","network_calls":0,"mutations":0}))
        return 0
    report=live_inventory(args.context,args.namespace) if args.live else demo()
    print(json.dumps(report,sort_keys=True))
    return 0
if __name__=="__main__":raise SystemExit(main())
