"""Chapter 120 offline enterprise platform capstone. Python 3.11+ stdlib only.

Models API admission, CDC outbox, Kafka-like partitions, idempotent projections,
SLO/capacity/DR/security checks and an audit-safe release decision.
No real network, databases, Kubernetes, cryptography or production mutations.
"""
from __future__ import annotations
import argparse,hashlib,json,math
from dataclasses import dataclass

class PlatformError(ValueError):pass
def require(condition,reason):
    if not condition:raise PlatformError(reason)
def numeric(value,name,positive=False):
    require(type(value) in (int,float) and math.isfinite(value) and (value>0 if positive else value>=0),name)
    return float(value)

@dataclass(frozen=True)
class Event:
    key:str
    version:int
    payload:str
    tenant:str
    def __post_init__(self):
        require(type(self.key) is str and bool(self.key) and len(self.key)<=100,"key")
        require(type(self.version) is int and self.version>=1,"version")
        require(type(self.payload) is str and len(self.payload)<=4096,"payload")
        require(type(self.tenant) is str and bool(self.tenant),"tenant")
    @property
    def digest(self):return hashlib.sha256(self.payload.encode()).hexdigest()

def authorized(role,principal_tenant,event):
    require(type(role) is str and type(principal_tenant) is str and type(event) is Event,"identity")
    return role in ("writer","admin") and (role=="admin" or principal_tenant==event.tenant)

class Pipeline:
    def __init__(self,partitions=4,queue_limit=100):
        require(type(partitions) is int and 1<=partitions<=128,"partitions")
        require(type(queue_limit) is int and queue_limit>=1,"queue_limit")
        self.partitions=partitions;self.queue_limit=queue_limit
        self.outbox=[];self.log=[[] for _ in range(partitions)]
        self.source={};self.search={};self.warehouse={};self.offsets=[0]*partitions
        self.dlq=[];self.metrics={"accepted":0,"published":0,"applied":0,"duplicates":0,"stale":0,"rejected":0}
    def submit(self,event,role="writer",principal_tenant=None):
        require(type(event) is Event,"event")
        if not authorized(role,event.tenant if principal_tenant is None else principal_tenant,event):
            self.metrics["rejected"]+=1;return False
        key=(event.tenant,event.key)
        current=self.source.get(key)
        if current and event.version<=current.version:
            self.metrics["stale"]+=1;return False
        if len(self.outbox)>=self.queue_limit:
            self.metrics["rejected"]+=1;return False
        self.source[key]=event
        self.outbox.append(event);self.metrics["accepted"]+=1
        return True
    def publish(self,max_batch=100):
        require(type(max_batch) is int and max_batch>=1,"max_batch")
        count=0
        while self.outbox and count<max_batch:
            e=self.outbox.pop(0)
            p=int(hashlib.sha256((e.tenant+":"+e.key).encode()).hexdigest(),16)%self.partitions
            self.log[p].append(e);count+=1;self.metrics["published"]+=1
        return count
    def consume(self,max_batch=100,fail_keys=None):
        require(type(max_batch) is int and max_batch>=1,"max_batch")
        require(fail_keys is None or (type(fail_keys) is set and all(type(x) is str for x in fail_keys)),"fail_keys")
        fail_keys=fail_keys or set()
        processed=0
        for p,partition in enumerate(self.log):
            while self.offsets[p]<len(partition) and processed<max_batch:
                e=partition[self.offsets[p]]
                if e.key in fail_keys:
                    # Do not commit offset after transient sink failure.
                    return processed
                key=(e.tenant,e.key)
                existing=self.search.get(key)
                if existing is None or e.version>existing.version:
                    self.search[key]=e;self.warehouse[key]=e;self.metrics["applied"]+=1
                else:self.metrics["duplicates"]+=1
                self.offsets[p]+=1;processed+=1
        return processed
    def lag(self):return sum(len(p)-o for p,o in zip(self.log,self.offsets))+len(self.outbox)
    def reconcile(self):
        missing=sorted(str(k) for k in self.source.keys()-self.search.keys())
        mismatch=sorted(str(k) for k in self.source.keys()&self.search.keys() if self.source[k].version!=self.search[k].version or self.source[k].digest!=self.search[k].digest or self.warehouse.get(k)!=self.search[k])
        extra=sorted(str(k) for k in self.search.keys()-self.source.keys())
        return {"missing":missing,"mismatched":mismatch,"extra":extra,"consistent":not(missing or mismatch or extra)}
    def report(self):return {"metrics":dict(self.metrics),"lag":self.lag(),"reconciliation":self.reconcile(),"partitions":self.partitions,"network_calls":0,"production_changes":0}

def capacity(rps,cpu_ms,target=.65,per_pod_rps=50,max_pods=20):
    numeric(rps,"rps");numeric(cpu_ms,"cpu_ms");numeric(target,"target",True);numeric(per_pod_rps,"per_pod_rps",True)
    require(target<=1 and type(max_pods) is int and max_pods>=1,"limits")
    cores=math.ceil(rps*cpu_ms/1000/target*1000)/1000
    needed=math.ceil(rps/per_pod_rps)
    return {"cores":cores,"pods_needed":needed,"pods_cap":max_pods,"saturated":needed>max_pods}
def slo(good,total,target=.999):
    require(type(good) is int and type(total) is int and 0<=good<=total,"counts")
    numeric(target,"target",True);require(target<1,"target")
    if not total:return {"status":"unknown","availability":None,"budget_remaining":None}
    allowed=(1-target)*total
    return {"status":"pass" if good/total>=target else "breach","availability":good/total,"budget_remaining":max(0,allowed-(total-good))}
def dr(lag_seconds,rpo_seconds,restore_minutes,rto_minutes,fenced,approved,verified):
    for name,v in (("lag",lag_seconds),("rpo",rpo_seconds),("restore",restore_minutes),("rto",rto_minutes)):numeric(v,name)
    require(all(type(x) is bool for x in (fenced,approved,verified)),"flags")
    blockers=[]
    if lag_seconds>rpo_seconds:blockers.append("rpo")
    if restore_minutes>rto_minutes:blockers.append("rto")
    if not fenced:blockers.append("fencing")
    if not approved:blockers.append("approval")
    if not verified:blockers.append("verification")
    return {"decision":"advisory-ready" if not blockers else "hold","blockers":blockers,"actual_failovers":0}
def acceptance(reconciled,lag,capacity_ok,slo_ok,dr_ok,security_ok,observability_ok,tests_ok,rollback_ok,approved):
    require(type(lag) is int and lag>=0,"lag")
    flags={"reconciliation":reconciled and lag==0,"capacity":capacity_ok,"slo":slo_ok,"disaster_recovery":dr_ok,"security":security_ok,"observability":observability_ok,"tests":tests_ok,"rollback":rollback_ok,"approval":approved}
    require(all(type(x) is bool for x in (reconciled,capacity_ok,slo_ok,dr_ok,security_ok,observability_ok,tests_ok,rollback_ok,approved)),"flags")
    weights={"reconciliation":15,"capacity":10,"slo":15,"disaster_recovery":15,"security":15,"observability":10,"tests":10,"rollback":5,"approval":5}
    score=sum(weights[k] for k,ok in flags.items() if ok)
    failed=sorted(k for k,ok in flags.items() if not ok)
    return {"score":score,"max_score":100,"failed":failed,"decision":"advisory-ready" if score>=90 and not failed else "hold","production_changes":0}
def demo(failure=False):
    p=Pipeline()
    for i in range(5):p.submit(Event(f"patient-{i}",1,f"synthetic-{i}","demo"))
    p.publish()
    p.consume(fail_keys={"patient-2"} if failure else set())
    r=p.report()
    cp=capacity(2000 if failure else 200,4)
    sl=slo(980 if failure else 1000,1000)
    recovery=dr(120 if failure else 10,60,40,60,not failure,True,True)
    acc=acceptance(r["reconciliation"]["consistent"],r["lag"],not cp["saturated"],sl["status"]=="pass",recovery["decision"]=="advisory-ready",True,True,True,True,True)
    result={"mode":"offline","pipeline":r,"capacity":cp,"slo":sl,"dr":recovery,"acceptance":acc,"network_calls":0,"production_changes":0}
    result["fingerprint"]=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
    return result
def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument("--dry-run",action="store_true");parser.add_argument("--failure",action="store_true")
    args=parser.parse_args(argv);print(json.dumps(demo(args.failure),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
