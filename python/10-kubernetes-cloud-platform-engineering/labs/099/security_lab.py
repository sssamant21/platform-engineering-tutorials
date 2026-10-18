"""Offline metadata-only cloud secrets governance. No SDKs, secret values, network or writes."""
from dataclasses import dataclass,asdict
import argparse,hashlib,hmac,json,re
class PolicyError(ValueError):pass
PROVIDERS={"aws","azure","gcp","kubernetes"}
ACTIONS={"review-access","propose-rotation","review-expiration"}
ID=re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./:@-]{0,255}$")
@dataclass(frozen=True)
class SecretMetadata:
    provider:str
    scope:str
    resource_id:str
    owner:str|None
    environment:str
    rotation_days:int|None
    age_days:int|None
    workload_identity:bool
    public_access:bool
    audit_enabled:bool
    def validate(self):
        if self.provider not in PROVIDERS:raise PolicyError("provider")
        if any(not isinstance(x,str) or not ID.fullmatch(x) for x in (self.scope,self.resource_id,self.environment)):raise PolicyError("identity")
        if self.owner is not None and not isinstance(self.owner,str):raise PolicyError("owner")
        if any(x is not None and (type(x) is not int or x<0) for x in (self.rotation_days,self.age_days)):raise PolicyError("age")
        if any(type(x) is not bool for x in (self.workload_identity,self.public_access,self.audit_enabled)):raise PolicyError("boolean")
    def key(self):
        self.validate()
        return self.provider,self.scope,self.resource_id
@dataclass(frozen=True)
class Finding:
    resource:str
    policy:str
    severity:str
def evaluate(resources):
    out=[];seen=set()
    for r in resources:
        if not isinstance(r,SecretMetadata):raise PolicyError("record")
        key=r.key()
        if key in seen:raise PolicyError("duplicate")
        seen.add(key);label="/".join(key)
        if r.environment=="prod" and not (r.owner or "").strip():out.append(Finding(label,"production-owner-required","high"))
        if r.public_access:out.append(Finding(label,"public-access-review","critical"))
        if not r.workload_identity:out.append(Finding(label,"workload-identity-preferred","medium"))
        if not r.audit_enabled:out.append(Finding(label,"audit-required","high"))
        if r.rotation_days is None or r.age_days is None:out.append(Finding(label,"rotation-age-unknown","medium"))
        elif r.age_days>r.rotation_days:out.append(Finding(label,"rotation-overdue","high"))
    return sorted(out,key=lambda f:(f.resource,f.policy))
def paginate(fetch,max_pages=20,max_items=1000):
    if type(max_pages) is not int or type(max_items) is not int or not 1<=max_pages<=100 or not 1<=max_items<=100000:raise PolicyError("budget")
    token=None;seen=set();items=[]
    for _ in range(max_pages):
        page=fetch(token)
        if not isinstance(page,dict) or not isinstance(page.get("items"),list):raise PolicyError("page")
        items.extend(page["items"])
        if len(items)>max_items:raise PolicyError("item limit")
        nxt=page.get("next")
        if nxt is None:return items
        if not isinstance(nxt,str) or not nxt or nxt in seen:raise PolicyError("pagination loop")
        seen.add(nxt);token=nxt
    raise PolicyError("page limit")
@dataclass(frozen=True)
class Plan:
    provider:str
    scope:str
    resource_id:str
    action:str
    ticket:str
    expected_version:str
    def digest(self):
        if self.provider not in PROVIDERS or self.action not in ACTIONS:raise PolicyError("unsafe action")
        if any(not isinstance(x,str) or not ID.fullmatch(x) for x in (self.scope,self.resource_id,self.ticket,self.expected_version)):raise PolicyError("plan")
        return hashlib.sha256(json.dumps(asdict(self),sort_keys=True,separators=(",",":")).encode()).hexdigest()
def approval_gate(plan,approval=None,now_epoch=0,dry_run=True):
    if type(now_epoch) is not int or now_epoch<0 or type(dry_run) is not bool:raise PolicyError("clock/mode")
    digest=plan.digest();a=approval or {}
    if not isinstance(a,dict):raise PolicyError("approval")
    valid=(a.get("approved") is True and isinstance(a.get("digest"),str) and hmac.compare_digest(a["digest"],digest)
           and isinstance(a.get("owner"),str) and bool(a["owner"].strip())
           and isinstance(a.get("approver"),str) and bool(a["approver"].strip())
           and a["approver"]!=a["owner"] and a.get("rollback_tested") is True
           and type(a.get("expires_at")) is int and a["expires_at"]>now_epoch)
    return {"plan_digest":digest,"approval_valid":valid,"decision":"advisory-only" if valid else "hold",
            "dry_run":dry_run,"mutations":0,"network_calls":0}
class FakePager:
    def __init__(self,items,page_size=2):
        if type(page_size) is not int or page_size<1:raise PolicyError("page size")
        self.items=items;self.page_size=page_size
    def fetch(self,token):
        i=int(token or 0)
        return {"items":self.items[i:i+self.page_size],
                "next":str(i+self.page_size) if i+self.page_size<len(self.items) else None}
def sample():
    return [
        SecretMetadata("aws","123456789012","arn:aws:secretsmanager:us-east-1:123456789012:secret:db-prod","dbre","prod",90,110,True,False,True),
        SecretMetadata("azure","sub-staging","kv/staging/db-password","platform","staging",60,20,True,False,True),
        SecretMetadata("gcp","sre-lab-12345","projects/sre-lab-12345/secrets/pg","dbre","prod",90,30,True,False,True),
        SecretMetadata("kubernetes","staging/namespace","secrets/db-credentials",None,"staging",30,None,False,False,False)]
def demo():
    resources=paginate(FakePager(sample(),1).fetch)
    plan=Plan("aws","123456789012",resources[0].resource_id,"propose-rotation","INC-099","v17")
    return {"mode":"offline-metadata-only","resources":len(resources),
            "findings":[asdict(f) for f in evaluate(resources)],"change":approval_gate(plan),
            "mutations":0,"network_calls":0,"secret_values_accessed":0}
def main(argv=None):
    p=argparse.ArgumentParser(description="Offline secrets governance lab")
    p.add_argument("--dry-run",action="store_true");p.parse_args(argv)
    print(json.dumps(demo(),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
