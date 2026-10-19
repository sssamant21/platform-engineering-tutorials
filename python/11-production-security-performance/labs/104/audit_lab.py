"""Offline compliance evidence and policy simulator. No cloud APIs or production changes."""
from dataclasses import dataclass,asdict
import argparse,hashlib,hmac,json,re
class AuditError(ValueError):pass
PROVIDERS={"aws","azure","gcp","kubernetes"}
ID=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@-]{0,199}$")
CONTROLS={"audit-logging","least-privilege","encryption-at-rest","owner-required","backup-verified"}
FRAMEWORKS={"CIS","NIST-800-53","SOC2"}
@dataclass(frozen=True)
class Evidence:
    provider:str
    scope:str
    resource_id:str
    control:str
    passed:bool
    observed_at:int
    owner:str|None
    source:str
    def validate(self):
        if self.provider not in PROVIDERS or self.control not in CONTROLS:raise AuditError("provider/control")
        for x in (self.scope,self.resource_id,self.source):
            if not isinstance(x,str) or not ID.fullmatch(x):raise AuditError("identity")
        if type(self.passed) is not bool or type(self.observed_at) is not int or self.observed_at<0:raise AuditError("evidence")
        if self.owner is not None and not isinstance(self.owner,str):raise AuditError("owner")
    def key(self):
        self.validate()
        return self.provider,self.scope,self.resource_id,self.control
@dataclass(frozen=True)
class ExceptionRecord:
    resource_key:tuple[str,str,str,str]
    ticket:str
    approver:str
    expires_at:int
    reason:str
    def validate(self):
        if not isinstance(self.resource_key,tuple) or len(self.resource_key)!=4:raise AuditError("exception key")
        if any(not isinstance(x,str) or not ID.fullmatch(x) for x in self.resource_key):raise AuditError("exception key")
        if any(not isinstance(x,str) or not ID.fullmatch(x) for x in (self.ticket,self.approver)):raise AuditError("exception identity")
        if type(self.expires_at) is not int or self.expires_at<0 or not isinstance(self.reason,str) or not self.reason.strip():raise AuditError("exception expiry/reason")
def canonical(data):return json.dumps(data,sort_keys=True,separators=(",",":"),ensure_ascii=True)
def digest(data):return hashlib.sha256(canonical(data).encode()).hexdigest()
def assess(records,*,now,complete=True,exceptions=(),max_age=3600):
    if type(now) is not int or now<0 or type(max_age) is not int or max_age<0 or type(complete) is not bool:raise AuditError("parameters")
    exemptions={}
    for e in exceptions:
        if not isinstance(e,ExceptionRecord):raise AuditError("exception")
        e.validate()
        if e.resource_key in exemptions:raise AuditError("duplicate exception")
        exemptions[e.resource_key]=e
    seen=set();findings=[];passed=0
    for e in records:
        if not isinstance(e,Evidence):raise AuditError("record")
        k=e.key()
        if k in seen:raise AuditError("duplicate evidence")
        seen.add(k)
        status="pass" if e.passed else "fail"
        if e.observed_at>now or now-e.observed_at>max_age:status="unknown"
        if e.control=="owner-required" and not (e.owner or "").strip():status="fail"
        ex=exemptions.get(k)
        if status=="fail" and ex and ex.expires_at>now:status="excepted"
        if status=="pass":passed+=1
        findings.append({"resource":"/".join(k[:3]),"control":e.control,"status":status,"source":e.source})
    findings.sort(key=lambda f:(f["resource"],f["control"]))
    return {"coverage":"complete" if complete else "unknown","passed":passed,"total":len(findings),
            "findings":findings,"report_sha256":digest(findings),"compliance_certified":False}
def drift(before,after):
    if before["coverage"]!="complete" or after["coverage"]!="complete":return {"new_failures":None,"status":"unknown"}
    old={(f["resource"],f["control"]) for f in before["findings"] if f["status"]=="fail"}
    new={(f["resource"],f["control"]) for f in after["findings"] if f["status"]=="fail"}
    return {"new_failures":len(new-old),"status":"evaluated"}
def paginate(fetch,max_pages=20,max_items=1000):
    if type(max_pages) is not int or type(max_items) is not int or not 1<=max_pages<=100 or not 1<=max_items<=100000:raise AuditError("budget")
    token=None;seen=set();items=[]
    for _ in range(max_pages):
        page=fetch(token)
        if not isinstance(page,dict) or not isinstance(page.get("items"),list):raise AuditError("page")
        items.extend(page["items"])
        if len(items)>max_items:raise AuditError("item budget")
        nxt=page.get("next")
        if nxt is None:return items
        if not isinstance(nxt,str) or not nxt or nxt in seen:raise AuditError("pagination loop")
        seen.add(nxt);token=nxt
    raise AuditError("page budget")
class Pager:
    def __init__(self,items,size=2):
        if type(size) is not int or size<1:raise AuditError("size")
        self.items=items;self.size=size
    def fetch(self,token):
        i=int(token or 0)
        return {"items":self.items[i:i+self.size],"next":str(i+self.size) if i+self.size<len(self.items) else None}
@dataclass(frozen=True)
class Plan:
    provider:str
    scope:str
    resource_id:str
    control:str
    ticket:str
    expected_evidence_digest:str
    def fingerprint(self):
        if self.provider not in PROVIDERS or self.control not in CONTROLS:raise AuditError("plan")
        for x in (self.scope,self.resource_id,self.ticket,self.expected_evidence_digest):
            if not isinstance(x,str) or not ID.fullmatch(x):raise AuditError("plan")
        return digest(asdict(self))
def approval_gate(plan,approval=None,now=0,dry_run=True):
    if type(now) is not int or now<0 or type(dry_run) is not bool:raise AuditError("mode")
    d=plan.fingerprint();a=approval or {}
    if not isinstance(a,dict):raise AuditError("approval")
    valid=(a.get("approved") is True and isinstance(a.get("digest"),str) and hmac.compare_digest(a["digest"],d)
           and isinstance(a.get("owner"),str) and bool(a["owner"].strip())
           and isinstance(a.get("approver"),str) and bool(a["approver"].strip()) and a["owner"]!=a["approver"]
           and type(a.get("expires_at")) is int and a["expires_at"]>now and a.get("rollback_tested") is True)
    return {"plan_digest":d,"approval_valid":valid,"decision":"advisory-only" if valid else "hold",
            "dry_run":dry_run,"mutations":0,"network_calls":0}
def samples():
    return [
        Evidence("aws","123456789012","rds/pg-prod","audit-logging",True,1000,"dbre","cloudtrail-ref-1"),
        Evidence("azure","sub-stage","aks/cluster","least-privilege",False,1000,"platform","activity-ref-2"),
        Evidence("gcp","project-stage","cloudsql/pg","encryption-at-rest",True,1000,"dbre","audit-ref-3"),
        Evidence("kubernetes","staging/ns","deployment/api","owner-required",True,1000,None,"k8s-audit-ref-4")]
def demo(partial=False):
    rows=paginate(Pager(samples(),1).fetch)
    report=assess(rows,now=1100,complete=not partial)
    plan=Plan("azure","sub-stage","aks/cluster","least-privilege","INC-104",report["report_sha256"])
    return {"mode":"offline-evidence-only","framework_mapping":["CIS","NIST-800-53","SOC2"],
            "report":report,"plan":approval_gate(plan),"mutations":0,"network_calls":0}
def main(argv=None):
    p=argparse.ArgumentParser(description="Offline security auditing lab")
    p.add_argument("--dry-run",action="store_true");p.add_argument("--partial",action="store_true")
    a=p.parse_args(argv);print(json.dumps(demo(a.partial),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
