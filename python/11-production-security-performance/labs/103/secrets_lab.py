"""Offline secrets/key lifecycle simulator. No secret values, encryption, SDKs or writes."""
from dataclasses import dataclass,asdict
import argparse,hashlib,hmac,json,re
class LabError(ValueError):pass
PROVIDERS={"aws","azure","gcp","kubernetes"}
ID=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@-]{0,199}$")
ACTIONS={"review-rotation","review-key-policy","review-envelope-design"}
@dataclass(frozen=True)
class Secret:
    provider:str
    scope:str
    resource_id:str
    environment:str
    owner:str|None
    key_version:str
    current_version:str
    age_days:int|None
    rotation_days:int|None
    encryption_at_rest:bool
    tls_required:bool
    workload_identity:bool
    audit_enabled:bool
    def validate(self):
        if self.provider not in PROVIDERS:raise LabError("provider")
        for x in (self.scope,self.resource_id,self.environment,self.key_version,self.current_version):
            if not isinstance(x,str) or not ID.fullmatch(x):raise LabError("identifier")
        if self.owner is not None and not isinstance(self.owner,str):raise LabError("owner")
        for x in (self.age_days,self.rotation_days):
            if x is not None and (type(x) is not int or x<0):raise LabError("rotation age")
        for x in (self.encryption_at_rest,self.tls_required,self.workload_identity,self.audit_enabled):
            if type(x) is not bool:raise LabError("boolean")
    def key(self):
        self.validate()
        return self.provider,self.scope,self.resource_id.casefold() if self.provider=="azure" else self.resource_id
def evaluate(records,complete=True):
    if type(complete) is not bool:raise LabError("completeness")
    findings=[];seen=set()
    for s in records:
        if not isinstance(s,Secret):raise LabError("record")
        key=s.key()
        if key in seen:raise LabError("duplicate")
        seen.add(key);ref="/".join(key)
        def flag(policy,severity):findings.append({"resource":ref,"policy":policy,"severity":severity})
        if s.environment=="prod" and not (s.owner or "").strip():flag("missing-owner","high")
        if not s.encryption_at_rest:flag("at-rest-unverified","high")
        if not s.tls_required:flag("tls-required","critical")
        if not s.workload_identity:flag("static-credential-review","medium")
        if not s.audit_enabled:flag("audit-disabled","high")
        if s.age_days is None or s.rotation_days is None:flag("rotation-unknown","medium")
        elif s.age_days>s.rotation_days:flag("rotation-overdue","high")
    return {"complete":complete,"findings":sorted(findings,key=lambda x:(x["resource"],x["policy"])),
            "compliance":"evaluated" if complete else "unknown"}
def paginate(fetch,max_pages=20,max_items=1000):
    if type(max_pages) is not int or type(max_items) is not int or not 1<=max_pages<=100 or not 1<=max_items<=100000:raise LabError("budget")
    token=None;seen=set();items=[]
    for _ in range(max_pages):
        page=fetch(token)
        if not isinstance(page,dict) or not isinstance(page.get("items"),list):raise LabError("page")
        items.extend(page["items"])
        if len(items)>max_items:raise LabError("item budget")
        nxt=page.get("next")
        if nxt is None:return items
        if not isinstance(nxt,str) or not nxt or nxt in seen:raise LabError("pagination loop")
        seen.add(nxt);token=nxt
    raise LabError("page budget")
class Pager:
    def __init__(self,items,size=2):
        if type(size) is not int or size<1:raise LabError("page size")
        self.items=items;self.size=size
    def fetch(self,token):
        i=int(token or 0)
        return {"items":self.items[i:i+self.size],"next":str(i+self.size) if i+self.size<len(self.items) else None}
@dataclass(frozen=True)
class RotationPlan:
    provider:str
    scope:str
    resource_id:str
    expected_version:str
    expected_key_version:str
    ticket:str
    action:str="review-rotation"
    def digest(self):
        if self.provider not in PROVIDERS or self.action not in ACTIONS:raise LabError("action")
        for x in (self.scope,self.resource_id,self.expected_version,self.expected_key_version,self.ticket):
            if not isinstance(x,str) or not ID.fullmatch(x):raise LabError("plan")
        return hashlib.sha256(json.dumps(asdict(self),sort_keys=True,separators=(",",":")).encode()).hexdigest()
def gate(plan,approval=None,now=0,dry_run=True):
    if type(now) is not int or now<0 or type(dry_run) is not bool:raise LabError("mode")
    digest=plan.digest();a=approval or {}
    if not isinstance(a,dict):raise LabError("approval")
    valid=(a.get("approved") is True and isinstance(a.get("digest"),str) and hmac.compare_digest(a["digest"],digest)
           and isinstance(a.get("owner"),str) and bool(a["owner"].strip())
           and isinstance(a.get("approver"),str) and bool(a["approver"].strip()) and a["owner"]!=a["approver"]
           and type(a.get("expires_at")) is int and a["expires_at"]>now
           and a.get("rollback_tested") is True and a.get("consumers_verified") is True)
    return {"digest":digest,"approval_valid":valid,"decision":"advisory-only" if valid else "hold",
            "dry_run":dry_run,"secret_reads":0,"cryptographic_operations":0,"mutations":0,"network_calls":0}
def samples():
    return [
        Secret("aws","123456789012","arn:aws:secretsmanager:us-east-1:123456789012:secret:pg","prod","dbre","kms-v2","v7",105,90,True,True,True,True),
        Secret("azure","sub-staging","kv/pg-password","staging","platform","key-v3","v2",15,60,True,True,True,True),
        Secret("gcp","sre-lab-123","projects/sre-lab-123/secrets/api","prod","sre","key-v1","v4",20,90,True,True,True,True),
        Secret("kubernetes","staging/ns","secret/db-creds","staging",None,"etcd-key-1","rv-3",None,None,False,True,False,False)]
def demo(partial=False):
    records=paginate(Pager(samples(),1).fetch)
    p=RotationPlan("aws","123456789012",records[0].resource_id,"v7","kms-v2","INC-103")
    return {"mode":"offline-metadata-only","resources":len(records),"policy":evaluate(records,not partial),
            "plan":gate(p),"secret_reads":0,"cryptographic_operations":0,"mutations":0,"network_calls":0}
def main(argv=None):
    p=argparse.ArgumentParser(description="Offline secrets/key lifecycle governance")
    p.add_argument("--dry-run",action="store_true");p.add_argument("--partial",action="store_true")
    a=p.parse_args(argv);print(json.dumps(demo(a.partial),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
