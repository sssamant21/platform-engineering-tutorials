"""AWS-shaped offline inventory, metrics and change-policy simulator."""
from __future__ import annotations
from dataclasses import dataclass,asdict
import argparse,hashlib,json,math,re
class LabError(ValueError):pass
REGION=re.compile(r"^[a-z]{2}(?:-gov)?-[a-z]+-\d+$")
ACCOUNT=re.compile(r"^\d{12}$")

@dataclass(frozen=True)
class Scope:
    account:str
    region:str
    def validate(self):
        if not ACCOUNT.fullmatch(self.account) or not REGION.fullmatch(self.region):
            raise LabError("invalid account/region")

def paginate(fetch,*,max_pages=20,max_items=1000):
    if not 1<=max_pages<=100 or not 1<=max_items<=100000:raise LabError("invalid budget")
    items=[];token=None;seen=set()
    for _ in range(max_pages):
        page=fetch(token)
        if not isinstance(page,dict) or not isinstance(page.get("items"),list):
            raise LabError("malformed page")
        items.extend(page["items"])
        if len(items)>max_items:raise LabError("item budget exceeded")
        nxt=page.get("next_token")
        if not nxt:return items
        if not isinstance(nxt,str) or nxt in seen:raise LabError("pagination token loop")
        seen.add(nxt);token=nxt
    raise LabError("page budget exceeded")

def inventory(scope,ec2,eks,rds,*,max_resources=1000):
    scope.validate()
    if not 1<=max_resources<=100000:raise LabError("invalid inventory budget")
    result={"ec2":[],"eks":[],"rds":[]};ids=set()
    for kind,records in (("ec2",ec2),("eks",eks),("rds",rds)):
        for rec in records:
            if not isinstance(rec,dict):raise LabError("invalid record")
            rid=rec.get("id");status=rec.get("status")
            if not isinstance(rid,str) or not rid or not isinstance(status,str) or not status:
                raise LabError("missing resource fields")
            if (kind,rid) in ids:raise LabError("duplicate resource")
            ids.add((kind,rid));result[kind].append({"id":rid,"status":status})
            if len(ids)>max_resources:raise LabError("resource budget exceeded")
    return {"scope":asdict(scope),"resources":result,"total":len(ids)}

def metric(value,timestamp,now,*,max_age=300):
    if type(value) not in (int,float) or not math.isfinite(value) or value<0:
        raise LabError("invalid metric")
    if type(timestamp) not in (int,float) or timestamp>now or now-timestamp>max_age:
        raise LabError("stale/future metric")
    return {"value":value,"age_seconds":now-timestamp,"fresh":True}

def capacity(cpu_pct,free_storage_gb,*,cpu_warn=80,storage_warn_gb=20):
    if any(type(x) not in (int,float) or not math.isfinite(x) for x in (cpu_pct,free_storage_gb)):
        raise LabError("invalid capacity")
    if not 0<=cpu_pct<=100 or free_storage_gb<0:raise LabError("invalid capacity range")
    return {"cpu_pressure":cpu_pct>=cpu_warn,"storage_pressure":free_storage_gb<storage_warn_gb}

def cost_proxy(hourly_rate,hours,instances):
    if any(type(x) not in (int,float) or not math.isfinite(x) or x<0 for x in (hourly_rate,hours)) or type(instances) is not int or not 0<=instances<=100000:
        raise LabError("invalid cost estimate")
    return round(hourly_rate*hours*instances,2)

@dataclass(frozen=True)
class Change:
    scope:Scope
    resource:str
    action:str
    incident:str
    def digest(self):
        self.scope.validate()
        if not self.resource or not self.incident or self.action!="review-capacity":
            raise LabError("action/resource not permitted")
        return hashlib.sha256(json.dumps(asdict(self),sort_keys=True,separators=(",",":")).encode()).hexdigest()

def approve(change,approval=None,*,dry_run=True):
    digest=change.digest();a=approval or {}
    valid=a.get("approved") is True and a.get("digest")==digest and a.get("rollback_tested") is True and a.get("owner") not in (None,"")
    return {"plan_digest":digest,"approved":valid,"dry_run":dry_run,
            "action":"advisory-only" if valid else "hold","mutations":0,"network_calls":0}

class FakePages:
    def __init__(self,items,page_size=2):
        self.items=items;self.size=page_size;self.calls=0
    def fetch(self,token):
        self.calls+=1;offset=int(token or 0)
        return {"items":self.items[offset:offset+self.size],
                "next_token":str(offset+self.size) if offset+self.size<len(self.items) else None}

def demo(pressure=False):
    scope=Scope("123456789012","us-east-1")
    rows=paginate(FakePages([{"id":"i-1","status":"running"},{"id":"i-2","status":"stopped"}],1).fetch)
    inv=inventory(scope,rows,[{"id":"eks-staging","status":"ACTIVE"}],[{"id":"postgres-staging","status":"available"}])
    change=Change(scope,"postgres-staging","review-capacity","INC-094")
    return {"mode":"offline-fake","inventory":inv,"capacity":capacity(94 if pressure else 40,8 if pressure else 100),
            "cost_proxy_usd":cost_proxy(.2,24,2),"change":approve(change),"network_calls":0,"mutations":0}

def main(argv=None):
    p=argparse.ArgumentParser(description="AWS cloud operations offline lab")
    p.add_argument("--pressure",action="store_true")
    p.add_argument("--dry-run",action="store_true")
    args=p.parse_args(argv)
    print(json.dumps(demo(args.pressure),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
