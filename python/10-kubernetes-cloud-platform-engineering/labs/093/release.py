"""Offline Kubernetes/GitOps progressive delivery simulator. No external writes."""
from __future__ import annotations
import argparse,hashlib,json,re
from dataclasses import dataclass,asdict
NAME=re.compile(r"^[a-z][a-z0-9-]{0,39}$")
DIGEST=re.compile(r"^sha256:[0-9a-f]{64}$")
class ReleaseError(ValueError):pass

@dataclass(frozen=True)
class Release:
    namespace:str
    service:str
    image:str
    replicas:int
    revision:str
    def validate(self):
        if not NAME.fullmatch(self.namespace) or not NAME.fullmatch(self.service):
            raise ReleaseError("invalid namespace/service")
        if not DIGEST.fullmatch(self.image):raise ReleaseError("immutable image digest required")
        if type(self.replicas) is not int or not 1<=self.replicas<=100:
            raise ReleaseError("invalid replicas")
        if not re.fullmatch(r"[a-zA-Z0-9._-]{1,64}",self.revision):
            raise ReleaseError("invalid revision")
    def digest(self):
        self.validate()
        return hashlib.sha256(json.dumps(asdict(self),sort_keys=True,separators=(",",":")).encode()).hexdigest()

@dataclass(frozen=True)
class Observed:
    generation:int
    observed_generation:int
    updated:int
    available:int
    image:str
    git_revision:str

def rollout(desired,observed):
    desired.validate()
    values=(observed.generation,observed.observed_generation,observed.updated,observed.available)
    if any(type(x) is not int or x<0 for x in values):raise ReleaseError("invalid rollout counters")
    if observed.observed_generation<observed.generation:return "progressing"
    if observed.image!=desired.image or observed.git_revision!=desired.revision:return "drift"
    if observed.updated<desired.replicas or observed.available<desired.replicas:return "progressing"
    return "healthy"

def progressive(samples,*,min_requests=100,max_error_rate=.01,max_p95_ms=500):
    if not 1<=min_requests<=100000 or not 0<=max_error_rate<1 or max_p95_ms<=0:
        raise ReleaseError("invalid canary policy")
    if not samples:return {"decision":"hold","reason":"no-telemetry"}
    total=0;errors=0;latencies=[]
    for s in samples:
        n=s.get("requests");bad=s.get("errors");values=s.get("latencies_ms")
        if type(n) is not int or type(bad) is not int or n<0 or not 0<=bad<=n:
            raise ReleaseError("invalid sample")
        if not isinstance(values,list) or len(values)!=n or any(type(v) not in (int,float) or not 0<=v<1e9 for v in values):
            raise ReleaseError("invalid latency sample")
        total+=n;errors+=bad;latencies.extend(values)
    if total<min_requests:return {"decision":"hold","reason":"insufficient-samples","requests":total}
    latencies.sort()
    p95=latencies[max(0,(95*total+99)//100-1)]
    error_rate=errors/total
    return {"decision":"promote" if error_rate<=max_error_rate and p95<=max_p95_ms else "rollback-proposal",
            "requests":total,"error_rate":error_rate,"p95_ms":p95}

def release_plan(desired,observed,samples,*,approvals=None,dry_run=True):
    status=rollout(desired,observed)
    gate=progressive(samples)
    a=approvals or {}
    approved=(a.get("approved") is True and a.get("plan_digest")==desired.digest()
              and a.get("rollback_tested") is True and a.get("owner_assigned") is True)
    action="hold"
    if status=="healthy" and gate["decision"]=="promote" and approved:
        action="propose-promotion"
    elif gate["decision"]=="rollback-proposal":
        action="propose-rollback" if approved else "hold-for-approval"
    return {"service":desired.service,"namespace":desired.namespace,"plan_digest":desired.digest(),
            "rollout":status,"canary":gate,"approval_valid":approved,"action":action,
            "dry_run":dry_run,"mutations":0,"network_calls":0}

def reconcile_git(desired,observed):
    status=rollout(desired,observed)
    return {"sync":"synced" if status=="healthy" else "out-of-sync",
            "action":"none" if status=="healthy" else "propose-gitops-reconcile","mutations":0}

def demo(fail=False):
    desired=Release("sre-lab","patient-api","sha256:"+"a"*64,2,"git-123")
    observed=Observed(3,3,2,2,desired.image,desired.revision)
    samples=[{"requests":100,"errors":8 if fail else 0,"latencies_ms":[600 if fail else 120]*100}]
    return release_plan(desired,observed,samples,approvals={"approved":True,
        "plan_digest":desired.digest(),"rollback_tested":True,"owner_assigned":True})

def main(argv=None):
    parser=argparse.ArgumentParser(description="Offline GitOps release simulation")
    parser.add_argument("--fail-canary",action="store_true")
    parser.add_argument("--dry-run",action="store_true")
    args=parser.parse_args(argv)
    print(json.dumps(demo(args.fail_canary),sort_keys=True))
    return 0
if __name__=="__main__":raise SystemExit(main())
