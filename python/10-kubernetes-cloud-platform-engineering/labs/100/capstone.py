"""Chapter 100 offline cloud-native capstone. No network, secret reads or writes."""
from dataclasses import dataclass,asdict
import argparse,hashlib,json,math,re
class PolicyError(ValueError):pass
PROVIDERS={"aws","azure","gcp","kubernetes"}
SAFE={"investigate","review-capacity","review-rotation","review-gitops"}
ID=re.compile(r"^(?!\.\.)/?[A-Za-z0-9][A-Za-z0-9_./:@-]{0,198}$")
@dataclass(frozen=True)
class Resource:
    provider:str
    scope:str
    uid:str
    service:str
    environment:str
    owner:str|None
    cost_monthly_usd:float
    storage_free_pct:float|None
    desired_revision:str
    observed_revision:str
    workload_identity:bool
    audit_enabled:bool
    secret_age_days:int|None
    secret_rotation_days:int|None
    def validate(self):
        if self.provider not in PROVIDERS:raise PolicyError("provider")
        if any(not isinstance(x,str) or not ID.fullmatch(x) for x in (self.scope,self.uid,self.service,self.environment,self.desired_revision,self.observed_revision)):raise PolicyError("identity")
        if self.owner is not None and not isinstance(self.owner,str):raise PolicyError("owner")
        if type(self.cost_monthly_usd) not in (int,float) or not math.isfinite(self.cost_monthly_usd) or self.cost_monthly_usd<0:raise PolicyError("cost")
        if self.storage_free_pct is not None and (type(self.storage_free_pct) not in (int,float) or not math.isfinite(self.storage_free_pct) or not 0<=self.storage_free_pct<=100):raise PolicyError("capacity")
        if any(v is not None and (type(v) is not int or v<0) for v in (self.secret_age_days,self.secret_rotation_days)):raise PolicyError("rotation")
        if type(self.workload_identity) is not bool or type(self.audit_enabled) is not bool:raise PolicyError("flags")
    def key(self):
        self.validate()
        return self.provider,self.scope,self.uid.lower() if self.provider=="azure" else self.uid
@dataclass(frozen=True)
class Signal:
    provider:str
    scope:str
    service:str
    bad_requests:int
    total_requests:int
    timestamp:int
    def validate(self,now,max_age=300):
        if self.provider not in PROVIDERS or any(not isinstance(x,str) or not x for x in (self.scope,self.service)):raise PolicyError("signal identity")
        if any(type(x) is not int for x in (self.bad_requests,self.total_requests,self.timestamp,now,max_age)):raise PolicyError("signal type")
        if not 0<=self.bad_requests<=self.total_requests or self.total_requests<=0:raise PolicyError("signal counts")
        if max_age<0 or self.timestamp>now or now-self.timestamp>max_age:raise PolicyError("stale or future")
def paginate(fetch,max_pages=20,max_items=1000):
    if type(max_pages) is not int or type(max_items) is not int or not 1<=max_pages<=100 or not 1<=max_items<=100000:raise PolicyError("budget")
    token=None;seen=set();items=[]
    for _ in range(max_pages):
        page=fetch(token)
        if not isinstance(page,dict) or not isinstance(page.get("items"),list):raise PolicyError("malformed page")
        items.extend(page["items"])
        if len(items)>max_items:raise PolicyError("item budget")
        token=page.get("next")
        if token is None:return items
        if not isinstance(token,str) or not token or token in seen:raise PolicyError("pagination loop")
        seen.add(token)
    raise PolicyError("page budget")
class FakePager:
    def __init__(self,items,size=2):
        if type(size) is not int or size<1:raise PolicyError("page size")
        self.items=items;self.size=size
    def fetch(self,token):
        i=int(token or 0)
        return {"items":self.items[i:i+self.size],"next":str(i+self.size) if i+self.size<len(self.items) else None}
def inventory(records,complete=True):
    if type(complete) is not bool:raise PolicyError("completeness")
    seen={}
    for r in records:
        if not isinstance(r,Resource):raise PolicyError("record")
        k=r.key()
        if k in seen:raise PolicyError("duplicate")
        seen[k]=r
    return {"complete":complete,"resources":seen}
def drift(old,new):
    a=old["resources"];b=new["resources"];valid=old["complete"] and new["complete"]
    return {"added":len(b.keys()-a.keys()),"removed":len(a.keys()-b.keys()) if valid else None,
            "changed":sum(a[k]!=b[k] for k in a.keys()&b.keys()),"removal_status":"verified" if valid else "unknown"}
def policies(records):
    findings=[]
    for r in records:
        key="/".join(r.key())
        if r.environment=="prod" and not (r.owner or "").strip():findings.append((key,"owner-required"))
        if r.storage_free_pct is not None and r.storage_free_pct<15:findings.append((key,"storage-pressure"))
        if r.desired_revision!=r.observed_revision:findings.append((key,"gitops-drift"))
        if not r.workload_identity:findings.append((key,"static-identity-review"))
        if not r.audit_enabled:findings.append((key,"audit-disabled"))
        if r.secret_age_days is None or r.secret_rotation_days is None:findings.append((key,"secret-age-unknown"))
        elif r.secret_age_days>r.secret_rotation_days:findings.append((key,"rotation-overdue"))
    return [{"resource":k,"policy":p} for k,p in sorted(findings)]
def slo(signals,now,target=.999):
    if type(target) not in (int,float) or not math.isfinite(target) or not 0<target<1:raise PolicyError("target")
    for s in signals:s.validate(now)
    total=sum(s.total_requests for s in signals);bad=sum(s.bad_requests for s in signals)
    if total==0:raise PolicyError("missing telemetry")
    budget=total*(1-target)
    return {"availability":round((total-bad)/total,6),"bad":bad,"total":total,
            "error_budget_events":round(budget,3),"consumption_ratio":round(bad/budget,3),"breached":bad/total>1-target}
def incidents(signals,now,bucket=300):
    if type(bucket) is not int or bucket<=0:raise PolicyError("bucket")
    groups={}
    for s in signals:
        s.validate(now)
        k=(s.service,s.timestamp//bucket)
        groups.setdefault(k,{})[(s.provider,s.scope,s.bad_requests,s.total_requests,s.timestamp)]=s
    return [{"id":hashlib.sha256(f"{service}|{time}".encode()).hexdigest()[:16],
             "service":service,"bucket":time,"signals":len(v),"providers":sorted({x.provider for x in v.values()}),
             "causality":"not-established"} for (service,time),v in sorted(groups.items())]
def finops(records):
    return {"synthetic_monthly_usd":round(sum(r.cost_monthly_usd for r in records),2),"not_actual_billing":True}
@dataclass(frozen=True)
class Plan:
    provider:str
    scope:str
    uid:str
    action:str
    ticket:str
    expected_revision:str
    def digest(self):
        if self.provider not in PROVIDERS or self.action not in SAFE:raise PolicyError("unsafe plan")
        if any(not isinstance(v,str) or not ID.fullmatch(v) for v in (self.scope,self.uid,self.ticket,self.expected_revision)):raise PolicyError("plan identity")
        return hashlib.sha256(json.dumps(asdict(self),sort_keys=True,separators=(",",":")).encode()).hexdigest()
def gate(plan,approval=None,now=0,dry_run=True):
    if type(now) is not int or now<0 or type(dry_run) is not bool:raise PolicyError("clock")
    digest=plan.digest();a=approval or {}
    if not isinstance(a,dict):raise PolicyError("approval")
    valid=(a.get("approved") is True and a.get("digest")==digest and a.get("rollback_tested") is True
           and isinstance(a.get("owner"),str) and bool(a["owner"].strip())
           and isinstance(a.get("approver"),str) and bool(a["approver"].strip()) and a["approver"]!=a["owner"]
           and type(a.get("expires_at")) is int and a["expires_at"]>now)
    return {"digest":digest,"approved":valid,"decision":"advisory-only" if valid else "hold",
            "dry_run":dry_run,"mutations":0,"network_calls":0}
def samples():
    return [
        Resource("aws","123456789012","rds-pg","patient-api","prod","dbre",480,12,"sha256:a1","sha256:a1",True,True,95,90),
        Resource("azure","sub-stage","/subscriptions/sub-stage/resourceGroups/rg/providers/Microsoft.ContainerService/managedClusters/aks","patient-api","staging","sre",300,35,"sha256:b1","sha256:b2",True,True,30,90),
        Resource("gcp","gcp-stage","projects/gcp-stage/instances/pg","patient-api","staging","dbre",250,60,"sha256:c1","sha256:c1",True,True,20,90),
        Resource("kubernetes","staging/ns","deployment/patient-api","patient-api","staging","platform",0,None,"sha256:d1","sha256:d1",False,False,None,None)]
def demo(partial=False):
    records=paginate(FakePager(samples(),1).fetch)
    signals=[Signal("aws","123456789012","patient-api",20,10000,1000),Signal("azure","sub-stage","patient-api",5,10000,1000),Signal("gcp","gcp-stage","patient-api",1,10000,1000)]
    plan=Plan("aws","123456789012","rds-pg","review-capacity","INC-100","sha256:a1")
    return {"mode":"offline","resources":len(records),"drift":drift(inventory(records),inventory(records[:-1],complete=not partial)),
            "findings":policies(records),"slo":slo(signals,1100),"incidents":incidents(signals,1100),
            "cost":finops(records),"change":gate(plan),"mutations":0,"network_calls":0,"secret_values_accessed":0}
def main(argv=None):
    p=argparse.ArgumentParser(description="Chapter 100 cloud-native offline capstone")
    p.add_argument("--dry-run",action="store_true");p.add_argument("--partial",action="store_true")
    a=p.parse_args(argv)
    print(json.dumps(demo(a.partial),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
