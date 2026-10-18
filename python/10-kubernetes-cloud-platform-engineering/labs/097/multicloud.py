"""Offline multi-cloud inventory and governance. No provider SDK or network calls."""
from __future__ import annotations
from dataclasses import dataclass,asdict
import argparse,hashlib,json,math,re

class GovernanceError(ValueError):pass
PROVIDERS={"aws","azure","gcp"}
NAME=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$")
@dataclass(frozen=True)
class Resource:
    provider:str
    scope:str
    native_id:str
    kind:str
    name:str
    state:str
    owner:str|None
    environment:str
    cost_center:str|None
    monthly_cost_usd:float
    storage_free_pct:float|None
    def key(self):
        self.validate()
        return (self.provider,self.scope,self.native_id.lower() if self.provider=="azure" else self.native_id)
    def validate(self):
        if self.provider not in PROVIDERS:raise GovernanceError("unsupported provider")
        if any(not isinstance(x,str) or not NAME.fullmatch(x) for x in
               (self.scope,self.native_id,self.kind,self.name,self.state,self.environment)):
            raise GovernanceError("invalid resource identity")
        if self.owner is not None and not isinstance(self.owner,str):raise GovernanceError("invalid owner")
        if self.cost_center is not None and not isinstance(self.cost_center,str):raise GovernanceError("invalid cost center")
        if type(self.monthly_cost_usd) not in (int,float) or not math.isfinite(self.monthly_cost_usd) or self.monthly_cost_usd<0:
            raise GovernanceError("invalid cost")
        if self.storage_free_pct is not None and (type(self.storage_free_pct) not in (int,float)
                or not math.isfinite(self.storage_free_pct) or not 0<=self.storage_free_pct<=100):
            raise GovernanceError("invalid storage headroom")

def paginate(fetch,*,max_pages=20,max_items=1000):
    if not 1<=max_pages<=100 or not 1<=max_items<=100000:raise GovernanceError("invalid budget")
    token=None;seen=set();out=[]
    for _ in range(max_pages):
        response=fetch(token)
        if not isinstance(response,dict) or not isinstance(response.get("items"),list):
            raise GovernanceError("malformed page")
        out.extend(response["items"])
        if len(out)>max_items:raise GovernanceError("item budget exceeded")
        nxt=response.get("next")
        if not nxt:return out
        if not isinstance(nxt,str) or nxt in seen:raise GovernanceError("pagination loop")
        seen.add(nxt);token=nxt
    raise GovernanceError("page budget exceeded")

def snapshot(records,*,complete=True):
    if type(complete) is not bool:raise GovernanceError("invalid completeness")
    data={}
    for r in records:
        if not isinstance(r,Resource):raise GovernanceError("invalid record")
        key=r.key()
        if key in data:raise GovernanceError("duplicate composite identity")
        data[key]=r
    return {"complete":complete,"resources":data}

def drift(before,after):
    old=before["resources"];new=after["resources"]
    added=sorted(new.keys()-old.keys());removed=sorted(old.keys()-new.keys())
    changed=sorted(k for k in old.keys()&new.keys() if old[k]!=new[k])
    return {"added":len(added),"removed":len(removed) if before["complete"] and after["complete"] else None,
            "changed":len(changed),"removal_status":"verified" if before["complete"] and after["complete"] else "unknown",
            "added_ids":[list(k) for k in added],"removed_ids":[list(k) for k in removed] if before["complete"] and after["complete"] else [],
            "changed_ids":[list(k) for k in changed]}

def compliance(records):
    findings=[]
    for r in records:
        key="/".join(r.key())
        if r.environment.lower()=="prod" and not (r.owner or "").strip():
            findings.append({"resource":key,"rule":"production-owner-required"})
        if not (r.cost_center or "").strip():
            findings.append({"resource":key,"rule":"cost-center-required"})
        if r.storage_free_pct is not None and r.storage_free_pct<15:
            findings.append({"resource":key,"rule":"storage-capacity-review"})
    return sorted(findings,key=lambda f:(f["resource"],f["rule"]))

def finops(records):
    rows=list(records)
    total=sum(r.monthly_cost_usd for r in rows)
    by_provider={p:round(sum(r.monthly_cost_usd for r in rows if r.provider==p),2) for p in sorted(PROVIDERS)}
    return {"estimated_monthly_usd":round(total,2),"by_provider":by_provider,
            "basis":"synthetic-estimate-not-provider-billing"}

def fingerprint(records,action="review-findings"):
    if action!="review-findings":raise GovernanceError("write actions forbidden")
    ordered=[asdict(r) for r in sorted(records,key=lambda r:r.key())]
    return hashlib.sha256(json.dumps({"action":action,"resources":ordered},sort_keys=True,separators=(",",":")).encode()).hexdigest()

def gate(records,approval=None,*,dry_run=True):
    digest=fingerprint(records);a=approval or {}
    valid=a.get("approved") is True and a.get("digest")==digest and a.get("rollback_tested") is True and isinstance(a.get("owner"),str) and bool(a["owner"].strip())
    return {"plan_digest":digest,"approved":valid,"action":"advisory-only" if valid else "hold",
            "dry_run":dry_run,"mutations":0,"network_calls":0}

class FakePager:
    def __init__(self,items,size=2):self.items=items;self.size=size
    def fetch(self,token):
        i=int(token or 0)
        return {"items":self.items[i:i+self.size],"next":str(i+self.size) if i+self.size<len(self.items) else None}

def examples():
    return [
        Resource("aws","123456789012","i-001","ec2","search-node","running","sre","prod","platform",200.0,12.0),
        Resource("azure","sub-staging","/subscriptions/sub-staging/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm1","vm","vm1","running","dbre","staging","data",150.0,55.0),
        Resource("gcp","sre-staging-12345","projects/sre-staging-12345/zones/us-central1-a/instances/vm1","compute","vm1","running",None,"prod",None,120.0,60.0)
    ]

def demo(partial=False):
    records=paginate(FakePager(examples(),1).fetch)
    before=snapshot(records)
    after=snapshot(records[:2],complete=not partial)
    return {"mode":"offline","inventory_count":len(records),"drift":drift(before,after),
            "findings":compliance(records),"cost":finops(records),"change":gate(records),
            "network_calls":0,"mutations":0}

def main(argv=None):
    p=argparse.ArgumentParser(description="Offline multi-cloud governance simulator")
    p.add_argument("--partial",action="store_true")
    p.add_argument("--dry-run",action="store_true")
    args=p.parse_args(argv)
    print(json.dumps(demo(args.partial),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
