"""Offline enterprise SRE/DBRE architecture simulator. Python 3.11+, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass,asdict
import argparse,json,math,re,hashlib
class ArchitectureError(ValueError):pass
SERVICES={"api","worker","postgres","elasticsearch","mongodb","redis","kafka","kubernetes"}
EDGES={("api","postgres"),("api","elasticsearch"),("api","mongodb"),("api","redis"),("api","kafka"),("worker","kafka"),("worker","postgres"),("worker","elasticsearch"),("worker","mongodb"),("kubernetes","api"),("kubernetes","worker")}
@dataclass(frozen=True)
class Dependency:
    source:str
    target:str
    timeout_ms:int
    max_inflight:int
    retries:int
    def validate(self):
        if (self.source,self.target) not in EDGES:raise ArchitectureError("unsupported edge")
        if type(self.timeout_ms) is not int or not 1<=self.timeout_ms<=60000:raise ArchitectureError("timeout")
        if type(self.max_inflight) is not int or not 1<=self.max_inflight<=1000:raise ArchitectureError("inflight")
        if type(self.retries) is not int or not 0<=self.retries<=3:raise ArchitectureError("retries")
def topology(edges):
    if not isinstance(edges,list):raise ArchitectureError("edges")
    seen=set();out=[]
    for e in edges:
        if not isinstance(e,Dependency):raise ArchitectureError("dependency")
        e.validate()
        key=(e.source,e.target)
        if key in seen:raise ArchitectureError("duplicate")
        seen.add(key);out.append(asdict(e))
    return {"edges":out,"count":len(out),"fingerprint":hashlib.sha256(json.dumps(out,sort_keys=True).encode()).hexdigest()}
def capacity(replicas,pool_size,backend_limit,reserved=0):
    if any(type(v) is not int for v in (replicas,pool_size,backend_limit,reserved)) or replicas<1 or pool_size<1 or backend_limit<1 or reserved<0 or reserved>=backend_limit:raise ArchitectureError("capacity")
    peak=replicas*pool_size
    return {"aggregate_connections":peak,"available_connections":backend_limit-reserved,"safe":peak<=backend_limit-reserved}
def admission(arrivals,active_limit,queue_limit):
    if any(type(v) is not int or v<0 for v in (arrivals,active_limit,queue_limit)) or active_limit<1:raise ArchitectureError("admission")
    active=min(arrivals,active_limit);waiting=min(max(0,arrivals-active),queue_limit)
    return {"active":active,"queued":waiting,"rejected":arrivals-active-waiting}
def percentile(samples,p):
    if not isinstance(samples,list) or not samples or any(type(x) not in (int,float) or not math.isfinite(x) or x<0 for x in samples):raise ArchitectureError("samples")
    if type(p) not in (int,float) or not math.isfinite(p) or not 0<=p<=100:raise ArchitectureError("percentile")
    a=sorted(samples);x=(len(a)-1)*p/100;lo=math.floor(x);hi=math.ceil(x)
    return a[lo]+(a[hi]-a[lo])*(x-lo)
def slo(good,total,target=.999):
    if type(good) is not int or type(total) is not int or not 0<=good<=total:raise ArchitectureError("events")
    if type(target) not in (int,float) or not math.isfinite(target) or not 0<target<1:raise ArchitectureError("target")
    budget=total*(1-target);bad=total-good
    return {"availability":None if total==0 else good/total,"remaining_budget":budget-bad,"status":"unknown" if total==0 else "breached" if bad>budget else "pass"}
def policy(role,action,secret_age,has_trace,has_rollback):
    if role not in {"reader","operator","admin"} or action not in {"read","deploy","delete"}:raise ArchitectureError("role/action")
    if type(secret_age) is not int or secret_age<0 or type(has_trace) is not bool or type(has_rollback) is not bool:raise ArchitectureError("evidence")
    allowed={"reader":{"read"},"operator":{"read","deploy"},"admin":{"read","deploy","delete"}}[role]
    blockers=[]
    if action not in allowed:blockers.append("rbac")
    if secret_age>=90:blockers.append("secret-rotation")
    if not has_trace:blockers.append("trace-coverage")
    if not has_rollback:blockers.append("rollback")
    return {"decision":"advisory-ready" if not blockers else "hold","blockers":blockers,"mutations":0}
def failure(service,kind):
    if service not in SERVICES or kind not in {"timeout","saturation","unavailable","lag"}:raise ArchitectureError("incident")
    guidance={"timeout":"verify deadlines and downstream health","saturation":"bound pools and shed load","unavailable":"fail closed and inspect failover","lag":"inspect backlog, throughput and ordering"}
    return {"service":service,"fault":kind,"action":guidance[kind],"faults_injected":0,"network_calls":0}
def demo(partial=False):
    edges=[Dependency("api","postgres",800,10,1),Dependency("api","elasticsearch",1200,5,1),Dependency("worker","kafka",1000,4,0),Dependency("kubernetes","api",1000,2,0)]
    report={"mode":"offline","topology":topology(edges),"capacity":capacity(4,20,100,10),"admission":admission(20,5,3),"p99_ms":percentile([10,20,30,40,50],99),"slo":slo(1000,1000),"policy":policy("operator","deploy",30,not partial,True),"incident":failure("postgres","saturation"),"mutations":0,"network_calls":0}
    report["sha256"]=hashlib.sha256(json.dumps(report,sort_keys=True).encode()).hexdigest()
    return report
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument("--dry-run",action="store_true");p.add_argument("--partial",action="store_true")
    a=p.parse_args(argv);print(json.dumps(demo(a.partial),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
