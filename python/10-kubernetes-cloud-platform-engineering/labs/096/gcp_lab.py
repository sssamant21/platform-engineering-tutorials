"""Offline GCP SRE/DBRE infrastructure simulator. No cloud requests or writes."""
from __future__ import annotations
from dataclasses import dataclass,asdict
import argparse,hashlib,json,math,re

class LabError(ValueError):pass
PROJECT=re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
LOCATION=re.compile(r"^[a-z]+(?:-[a-z]+)+[0-9](?:-[a-z])?$")

@dataclass(frozen=True)
class Scope:
    project:str
    location:str
    def validate(self):
        if not PROJECT.fullmatch(self.project) or not LOCATION.fullmatch(self.location):
            raise LabError("invalid project/location")

def paginate(fetch,*,max_pages=20,max_items=1000):
    if not 1<=max_pages<=100 or not 1<=max_items<=100000:raise LabError("invalid budget")
    token=None;seen=set();out=[]
    for _ in range(max_pages):
        page=fetch(token)
        if not isinstance(page,dict) or not isinstance(page.get("items"),list):
            raise LabError("malformed page")
        out.extend(page["items"])
        if len(out)>max_items:raise LabError("item budget exceeded")
        nxt=page.get("next_page_token")
        if not nxt:return out
        if not isinstance(nxt,str) or nxt in seen:raise LabError("pagination loop")
        seen.add(nxt);token=nxt
    raise LabError("page budget exceeded")

def inventory(scope,*,compute=(),gke=(),cloudsql=(),max_items=1000):
    scope.validate()
    if not 1<=max_items<=100000:raise LabError("invalid inventory budget")
    result={};seen=set()
    for kind,items in (("compute",compute),("gke",gke),("cloudsql",cloudsql)):
        result[kind]=[]
        for obj in items:
            if not isinstance(obj,dict) or not isinstance(obj.get("name"),str) or not obj["name"]:
                raise LabError("invalid resource name")
            if not isinstance(obj.get("status"),str) or not obj["status"]:
                raise LabError("invalid resource status")
            key=(kind,obj["name"])
            if key in seen:raise LabError("duplicate resource")
            seen.add(key)
            if len(seen)>max_items:raise LabError("inventory budget exceeded")
            result[kind].append({"name":obj["name"],"status":obj["status"]})
    return {"scope":asdict(scope),"resources":result,"total":len(seen)}

def metric(value,observed_at,now,*,max_age=300):
    if type(value) not in (int,float) or not math.isfinite(value) or value<0:
        raise LabError("invalid metric")
    if type(observed_at) not in (int,float) or not math.isfinite(observed_at) or observed_at>now or now-observed_at>max_age:
        raise LabError("missing/stale/future metric")
    return {"value":value,"age_seconds":now-observed_at,"fresh":True}

def capacity(cpu_pct,storage_free_pct,*,cpu_warn=85,storage_warn=15):
    values=(cpu_pct,storage_free_pct,cpu_warn,storage_warn)
    if any(type(x) not in (int,float) or not math.isfinite(x) or not 0<=x<=100 for x in values):
        raise LabError("invalid capacity")
    return {"cpu_pressure":cpu_pct>=cpu_warn,"storage_pressure":storage_free_pct<=storage_warn}

def cost_proxy(hourly_usd,hours,quantity):
    if any(type(x) not in (int,float) or not math.isfinite(x) or x<0 for x in (hourly_usd,hours)):
        raise LabError("invalid cost")
    if type(quantity) is not int or not 0<=quantity<=100000:raise LabError("invalid quantity")
    return round(hourly_usd*hours*quantity,2)

@dataclass(frozen=True)
class Plan:
    scope:Scope
    resource:str
    action:str
    incident:str
    def digest(self):
        self.scope.validate()
        if not self.resource or self.action!="review-capacity" or not self.incident:
            raise LabError("invalid plan")
        return hashlib.sha256(json.dumps(asdict(self),sort_keys=True,separators=(",",":")).encode()).hexdigest()

def gate(plan,approval=None,*,dry_run=True):
    digest=plan.digest();a=approval or {}
    approved=(a.get("approved") is True and a.get("digest")==digest and
              a.get("rollback_tested") is True and isinstance(a.get("owner"),str) and bool(a.get("owner")))
    return {"plan_digest":digest,"approved":approved,"action":"advisory-only" if approved else "hold",
            "dry_run":dry_run,"mutations":0,"network_calls":0}

class FakePager:
    def __init__(self,items,size=2):self.items=items;self.size=size
    def fetch(self,token):
        i=int(token or 0)
        return {"items":self.items[i:i+self.size],
                "next_page_token":str(i+self.size) if i+self.size<len(self.items) else None}

def demo(pressure_mode=False):
    scope=Scope("sre-lab-12345","us-central1-a")
    rows=paginate(FakePager([{"name":"vm1","status":"RUNNING"},{"name":"vm2","status":"TERMINATED"}],1).fetch)
    inv=inventory(scope,compute=rows,gke=[{"name":"staging-gke","status":"RUNNING"}],
                  cloudsql=[{"name":"postgres-staging","status":"RUNNABLE"}])
    plan=Plan(scope,"vm1","review-capacity","INC-096")
    return {"mode":"offline-fake","inventory":inv,
            "capacity":capacity(92 if pressure_mode else 35,8 if pressure_mode else 55),
            "estimated_usd":cost_proxy(.3,24,2),"change":gate(plan),
            "mutations":0,"network_calls":0}

def main(argv=None):
    p=argparse.ArgumentParser(description="Offline GCP operations simulator")
    p.add_argument("--pressure",action="store_true")
    p.add_argument("--dry-run",action="store_true")
    args=p.parse_args(argv)
    print(json.dumps(demo(args.pressure),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
