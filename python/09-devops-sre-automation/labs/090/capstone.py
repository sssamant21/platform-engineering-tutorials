"""Chapter 090 offline SRE capstone: synthetic data, read-only analysis, sandbox marker only."""
from __future__ import annotations
import argparse
from dataclasses import asdict,dataclass
from datetime import datetime,timezone
import hashlib,json,math,os
from pathlib import Path
import re,time

class PolicyError(ValueError):pass
ID=re.compile(r"^INC-[0-9]{4,12}$")
NAME=re.compile(r"^[a-z][a-z0-9-]{0,39}$")
ACTION="write-sandbox-incident-marker"

@dataclass(frozen=True)
class Resource:
    service:str
    kind:str
    name:str
    healthy:bool
    def validate(self):
        if not NAME.fullmatch(self.service) or not NAME.fullmatch(self.name):
            raise PolicyError("invalid resource scope")
        if self.kind not in ("pod","deployment","database","pipeline") or type(self.healthy) is not bool:
            raise PolicyError("invalid resource")

@dataclass(frozen=True)
class Metrics:
    cpu:float
    memory:float
    disk:float
    observed_at:float
    def validate(self,now,max_age=300):
        if any(not math.isfinite(x) or not 0<=x<=100 for x in (self.cpu,self.memory,self.disk)):
            raise PolicyError("invalid utilization")
        if not math.isfinite(self.observed_at) or not now-max_age<=self.observed_at<=now:
            raise PolicyError("stale or future monitoring sample")

@dataclass(frozen=True)
class Plan:
    incident_id:str
    service:str
    rationale:str
    action:str=ACTION
    def validate(self):
        if not ID.fullmatch(self.incident_id) or not NAME.fullmatch(self.service):
            raise PolicyError("invalid incident scope")
        if self.action!=ACTION or self.rationale not in ("slo-burn","resource-pressure","manual-review"):
            raise PolicyError("action/rationale not allowlisted")
    def digest(self):
        self.validate()
        return hashlib.sha256(json.dumps(asdict(self),sort_keys=True,separators=(",",":")).encode()).hexdigest()

def inventory(resources,service,max_records=100):
    if not NAME.fullmatch(service) or not 1<=max_records<=1000:
        raise PolicyError("invalid inventory scope or budget")
    if len(resources)>max_records:raise PolicyError("inventory budget exceeded")
    for r in resources:r.validate()
    selected=[r for r in resources if r.service==service]
    return {"total":len(selected),"unhealthy":sum(not r.healthy for r in selected),
            "kinds":sorted(set(r.kind for r in selected))}

def slo(outcomes,target=.99,min_events=20):
    if not math.isfinite(target) or not 0<target<1 or not 1<=min_events<=100000:
        raise PolicyError("invalid SLO policy")
    if len(outcomes)>100000 or any(type(x) is not bool for x in outcomes):
        raise PolicyError("invalid SLI events")
    n=len(outcomes)
    if n==0:
        return {"total":0,"availability":None,"remaining_budget":None,"burn_rate":None,
                "sufficient":False,"exhausted":None}
    bad=n-sum(outcomes)
    allowed=n*(1-target)
    return {"total":n,"availability":(n-bad)/n,"remaining_budget":allowed-bad,
            "burn_rate":(bad/n)/(1-target),"sufficient":n>=min_events,
            "exhausted":bad>allowed}

REQUIRED=("telemetry_fresh","owner_assigned","rollback_tested","backup_restore_tested",
          "paging_route_tested","capacity_reviewed")

def assess(resources,metrics,outcomes,checks,incident_id,service,now,*,target=.99,open_sev1=False):
    if type(open_sev1) is not bool:raise PolicyError("invalid incident flag")
    if not ID.fullmatch(incident_id):raise PolicyError("invalid incident ID")
    metrics.validate(now)
    inv=inventory(resources,service)
    reliability=slo(outcomes,target)
    if any(type(checks.get(k)) is not bool for k in REQUIRED):
        reasons=["missing-readiness-evidence"]
    else:
        reasons=[k for k in REQUIRED if not checks[k]]
    if open_sev1:reasons.append("active-sev1")
    if inv["total"]==0:reasons.append("missing-inventory")
    if inv["unhealthy"]:reasons.append("unhealthy-resource")
    if not reliability["sufficient"]:reasons.append("insufficient-sli-samples")
    if reliability["exhausted"]:reasons.append("error-budget-exhausted")
    if metrics.cpu>=90 or metrics.memory>=90 or metrics.disk>=90:
        reasons.append("resource-pressure")
    rationale=("slo-burn" if reliability["sufficient"] and reliability["burn_rate"]>=2
               else "resource-pressure" if "resource-pressure" in reasons else "manual-review")
    plan=Plan(incident_id,service,rationale)
    return {"inventory":inv,"metrics":asdict(metrics),"slo":reliability,
            "readiness":{"ready":not reasons,"reasons":reasons},
            "plan":asdict(plan),"plan_digest":plan.digest(),
            "advisory_only":True}

def _audit(root,event):
    path=root/"audit.jsonl"
    if path.is_symlink():raise PolicyError("audit symlink forbidden")
    with path.open("a",encoding="utf-8") as stream:
        stream.write(json.dumps({"at":datetime.now(timezone.utc).isoformat(),**event},sort_keys=True)+"\n")
        stream.flush()
        os.fsync(stream.fileno())

def apply_marker(plan,root,*,apply=False,approval_digest=None,approver=None,expires=None,now=None):
    plan.validate()
    digest=plan.digest()
    if not apply:
        return {"status":"dry-run","plan_digest":digest,"mutations":0,"network_calls":0}
    current=time.time() if now is None else now
    if (approval_digest!=digest or not isinstance(approver,str) or not NAME.fullmatch(approver)
            or expires is None or not math.isfinite(expires)
            or not current<=expires<=current+3600):
        raise PolicyError("simulated approval rejected")
    root=Path(root).resolve(strict=True)
    if not root.is_dir():raise PolicyError("sandbox missing")
    marker=root/(plan.incident_id+"-"+plan.service+".marker")
    if marker.is_symlink():raise PolicyError("marker symlink forbidden")
    try:
        fd=os.open(marker,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError:
        try: previous=json.loads(marker.read_text(encoding="utf-8"))
        except (OSError,ValueError) as exc:raise PolicyError("unknown previous outcome") from exc
        if previous.get("plan_digest")!=digest:raise PolicyError("idempotency conflict")
        _audit(root,{"event":"duplicate","incident_id":plan.incident_id,"plan_digest":digest,"actor":approver})
        return {"status":"already-applied","plan_digest":digest}
    with os.fdopen(fd,"w",encoding="utf-8") as stream:
        json.dump({"plan_digest":digest,"incident_id":plan.incident_id},stream)
        stream.flush()
        os.fsync(stream.fileno())
    _audit(root,{"event":"applied","incident_id":plan.incident_id,
                 "plan_digest":digest,"actor":approver,"action":plan.action})
    return {"status":"applied","plan_digest":digest,"marker":marker.name}

def fixtures(now=1000.0,failures=0,pressure=False):
    if not 0<=failures<=100:raise PolicyError("invalid fixture")
    resources=[Resource("postgres-health","database","primary",True),
               Resource("postgres-health","pod","replica",True)]
    metrics=Metrics(95 if pressure else 35,40,94 if pressure else 42,now-10)
    outcomes=[False]*failures+[True]*(100-failures)
    checks={key:True for key in REQUIRED}
    return resources,metrics,outcomes,checks

def main(argv=None):
    p=argparse.ArgumentParser(description="Offline SRE capstone; sandbox-only apply")
    p.add_argument("--incident",default="INC-1001")
    p.add_argument("--service",default="postgres-health")
    p.add_argument("--failures",type=int,default=0)
    p.add_argument("--pressure",action="store_true")
    p.add_argument("--dry-run",action="store_true")
    p.add_argument("--apply",action="store_true")
    p.add_argument("--sandbox",type=Path)
    p.add_argument("--approval-digest")
    p.add_argument("--approver")
    p.add_argument("--expires",type=float)
    args=p.parse_args(argv)
    now=time.time()
    try:
        resources,metrics,outcomes,checks=fixtures(now,args.failures,args.pressure)
        report=assess(resources,metrics,outcomes,checks,args.incident,args.service,now)
        if args.apply:
            if args.sandbox is None:raise PolicyError("sandbox required")
            plan=Plan(**report["plan"])
            report["execution"]=apply_marker(plan,args.sandbox,apply=True,
                approval_digest=args.approval_digest,approver=args.approver,
                expires=args.expires,now=now)
        else:
            report["execution"]={"status":"dry-run","mutations":0,"network_calls":0}
    except (PolicyError,OSError,OverflowError):
        print(json.dumps({"status":"rejected"}))
        return 2
    print(json.dumps(report,sort_keys=True))
    return 0

if __name__=="__main__":raise SystemExit(main())
