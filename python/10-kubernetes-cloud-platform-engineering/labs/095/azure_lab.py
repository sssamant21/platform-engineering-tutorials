"""Offline Azure cloud-operations lab: no network access or resource mutation."""
from __future__ import annotations
from dataclasses import dataclass,asdict
import argparse,hashlib,json,math,re

class LabError(ValueError):pass
SUB=re.compile(r"^[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")
NAME=re.compile(r"^[A-Za-z0-9_.()-]{1,90}$")

@dataclass(frozen=True)
class Scope:
    subscription:str
    resource_group:str
    def validate(self):
        if not SUB.fullmatch(self.subscription) or not NAME.fullmatch(self.resource_group):
            raise LabError("invalid subscription/resource group")

def pages(fetch,*,max_pages=20,max_items=1000):
    if not 1<=max_pages<=100 or not 1<=max_items<=100000:raise LabError("invalid page/item budget")
    token=None;seen=set();out=[]
    for _ in range(max_pages):
        page=fetch(token)
        if not isinstance(page,dict) or not isinstance(page.get("items"),list):
            raise LabError("malformed page")
        out.extend(page["items"])
        if len(out)>max_items:raise LabError("item budget exceeded")
        nxt=page.get("next")
        if not nxt:return out
        if not isinstance(nxt,str) or nxt in seen:raise LabError("continuation loop")
        seen.add(nxt);token=nxt
    raise LabError("page budget exceeded")

def inventory(scope,*,vms=(),aks=(),postgres=(),max_items=1000):
    scope.validate()
    if not 1<=max_items<=100000:raise LabError("invalid inventory budget")
    resources={};seen=set()
    for kind,records in (("vms",vms),("aks",aks),("postgres",postgres)):
        resources[kind]=[]
        for item in records:
            if not isinstance(item,dict) or not isinstance(item.get("id"),str) or not item["id"].startswith("/subscriptions/"+scope.subscription+"/"):
                raise LabError("resource ID outside approved subscription")
            if not isinstance(item.get("state"),str) or not item["state"]:
                raise LabError("missing provisioning state")
            key=(kind,item["id"].lower())
            if key in seen:raise LabError("duplicate resource")
            seen.add(key)
            if len(seen)>max_items:raise LabError("resource budget exceeded")
            resources[kind].append({"id":item["id"],"state":item["state"]})
    return {"scope":asdict(scope),"resources":resources,"total":len(seen)}

def observation(value,ts,now,*,max_age=300):
    if type(value) not in (int,float) or not math.isfinite(value) or value<0:
        raise LabError("invalid metric value")
    if type(ts) not in (int,float) or not math.isfinite(ts) or ts>now or now-ts>max_age:
        raise LabError("missing/stale/future metric")
    return {"value":value,"age_seconds":now-ts,"fresh":True}

def pressure(cpu_pct,storage_free_pct,*,cpu_limit=85,storage_floor=15):
    if any(type(x) not in (int,float) or not math.isfinite(x) or not 0<=x<=100
           for x in (cpu_pct,storage_free_pct,cpu_limit,storage_floor)):
        raise LabError("invalid capacity")
    return {"cpu_pressure":cpu_pct>=cpu_limit,"storage_pressure":storage_free_pct<=storage_floor}

def cost_proxy(hourly_rate,hours,quantity):
    if any(type(x) not in (int,float) or not math.isfinite(x) or x<0 for x in (hourly_rate,hours)):
        raise LabError("invalid cost")
    if type(quantity) is not int or not 0<=quantity<=100000:raise LabError("invalid quantity")
    return round(hourly_rate*hours*quantity,2)

@dataclass(frozen=True)
class Plan:
    scope:Scope
    resource_id:str
    action:str
    incident:str
    def digest(self):
        self.scope.validate()
        prefix=f"/subscriptions/{self.scope.subscription}/resourceGroups/{self.scope.resource_group}/"
        if not self.resource_id.lower().startswith(prefix.lower()) or self.action!="review-capacity" or not self.incident:
            raise LabError("invalid scope/action/incident")
        return hashlib.sha256(json.dumps(asdict(self),sort_keys=True,separators=(",",":")).encode()).hexdigest()

def gate(plan,approval=None,*,dry_run=True):
    digest=plan.digest();a=approval or {}
    approved=(a.get("approved") is True and a.get("digest")==digest
              and a.get("rollback_tested") is True and isinstance(a.get("owner"),str)
              and bool(a.get("owner")))
    return {"plan_digest":digest,"approved":approved,"action":"advisory-only" if approved else "hold",
            "dry_run":dry_run,"network_calls":0,"mutations":0}

class FakePager:
    def __init__(self,items,size=2):self.items=items;self.size=size;self.calls=0
    def fetch(self,token):
        self.calls+=1;i=int(token or 0)
        return {"items":self.items[i:i+self.size],
                "next":str(i+self.size) if i+self.size<len(self.items) else None}

def demo(high_pressure=False):
    scope=Scope("11111111-2222-3333-4444-555555555555","sre-staging")
    rid=f"/subscriptions/{scope.subscription}/resourceGroups/{scope.resource_group}/providers/Microsoft.Compute/virtualMachines/vm01"
    records=pages(FakePager([{"id":rid,"state":"Succeeded"}],1).fetch)
    inv=inventory(scope,vms=records)
    plan=Plan(scope,rid,"review-capacity","INC-095")
    return {"mode":"offline-fake","inventory":inv,
            "capacity":pressure(92 if high_pressure else 40,8 if high_pressure else 60),
            "estimated_usd":cost_proxy(.25,24,1),"change":gate(plan),"network_calls":0,"mutations":0}

def main(argv=None):
    parser=argparse.ArgumentParser(description="Offline Azure operations lab")
    parser.add_argument("--pressure",action="store_true")
    parser.add_argument("--dry-run",action="store_true")
    args=parser.parse_args(argv)
    print(json.dumps(demo(args.pressure),sort_keys=True))
    return 0
if __name__=="__main__":raise SystemExit(main())
