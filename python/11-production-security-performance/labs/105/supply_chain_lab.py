"""Chapter 105 offline supply-chain policy lab. No package installation, network, signing or mutation."""
from dataclasses import dataclass,asdict
import argparse,hashlib,hmac,json,re
class SupplyError(ValueError):pass
NAME=re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
VERSION=re.compile(r"^[0-9]+(?:\.[0-9]+){1,3}(?:[a-zA-Z0-9.-]+)?$")
HEX=re.compile(r"^[a-fA-F0-9]{64}$")
ECOSYSTEMS={"pypi"}
@dataclass(frozen=True)
class Dependency:
    name:str
    version:str
    sha256:str
    direct:bool
    source:str
    def validate(self):
        if not isinstance(self.name,str) or not NAME.fullmatch(self.name):raise SupplyError("package")
        if not isinstance(self.version,str) or not VERSION.fullmatch(self.version):raise SupplyError("version")
        if not isinstance(self.sha256,str) or not HEX.fullmatch(self.sha256):raise SupplyError("digest")
        if type(self.direct) is not bool or self.source!="pypi":raise SupplyError("source")
    def key(self):
        self.validate()
        return re.sub(r"[-_.]+","-",self.name).lower()
@dataclass(frozen=True)
class Finding:
    package:str
    version:str
    advisory:str
    severity:str
    def validate(self):
        if any(not isinstance(x,str) or not NAME.fullmatch(x) for x in (self.package,self.advisory)):raise SupplyError("finding")
        if not isinstance(self.version,str) or not VERSION.fullmatch(self.version):raise SupplyError("finding")
        if self.severity not in {"low","medium","high","critical"}:raise SupplyError("severity")
def canonical(data):return json.dumps(data,sort_keys=True,separators=(",",":"),ensure_ascii=True)
def sha(data):return hashlib.sha256(canonical(data).encode()).hexdigest()
def inventory(deps,complete=True):
    if type(complete) is not bool:raise SupplyError("coverage")
    entries={}
    for d in deps:
        if not isinstance(d,Dependency):raise SupplyError("record")
        k=d.key()
        if k in entries:raise SupplyError("duplicate normalized package")
        entries[k]=d
    return {"complete":complete,"entries":entries}
def sbom(deps,complete=True):
    inv=inventory(deps,complete)
    packages=[{"name":d.key(),"version":d.version,"sha256":d.sha256.lower(),"direct":d.direct,"source":d.source} for d in inv["entries"].values()]
    packages.sort(key=lambda x:x["name"])
    return {"format":"educational-json-not-cyclonedx-or-spdx","complete":complete,"packages":packages,"digest":sha(packages)}
def assess(deps,findings,complete=True):
    inv=inventory(deps,complete);issues=[]
    for f in findings:
        if not isinstance(f,Finding):raise SupplyError("finding")
        f.validate();key=re.sub(r"[-_.]+","-",f.package).lower()
        d=inv["entries"].get(key)
        if d and d.version==f.version:issues.append({"package":key,"advisory":f.advisory,"severity":f.severity})
    issues.sort(key=lambda x:(x["package"],x["advisory"]))
    return {"coverage":"complete" if complete else "unknown","vulnerabilities":issues,
            "risk":"unknown" if not complete else "review" if issues else "no-matches-in-synthetic-feed",
            "feed":"synthetic-not-live"}
def drift(before,after):
    if not before["complete"] or not after["complete"]:return {"removed":None,"changed":None,"status":"unknown"}
    a=before["entries"];b=after["entries"]
    return {"removed":len(a.keys()-b.keys()),"changed":sum(a[k]!=b[k] for k in a.keys()&b.keys()),"status":"evaluated"}
def verify_artifact(data,expected):
    if not isinstance(data,bytes) or not isinstance(expected,str) or not HEX.fullmatch(expected):raise SupplyError("artifact")
    return hmac.compare_digest(hashlib.sha256(data).hexdigest(),expected.lower())
def paginate(fetch,max_pages=20,max_items=1000):
    if type(max_pages) is not int or type(max_items) is not int or not 1<=max_pages<=100 or not 1<=max_items<=100000:raise SupplyError("budget")
    token=None;seen=set();items=[]
    for _ in range(max_pages):
        page=fetch(token)
        if not isinstance(page,dict) or not isinstance(page.get("items"),list):raise SupplyError("page")
        items.extend(page["items"])
        if len(items)>max_items:raise SupplyError("item budget")
        nxt=page.get("next")
        if nxt is None:return items
        if not isinstance(nxt,str) or not nxt or nxt in seen:raise SupplyError("pagination loop")
        seen.add(nxt);token=nxt
    raise SupplyError("page budget")
class Pager:
    def __init__(self,items,size=2):
        if type(size) is not int or size<1:raise SupplyError("size")
        self.items=items;self.size=size
    def fetch(self,token):
        i=int(token or 0)
        return {"items":self.items[i:i+self.size],"next":str(i+self.size) if i+self.size<len(self.items) else None}
@dataclass(frozen=True)
class ReleasePlan:
    repository:str
    commit_sha:str
    artifact_sha256:str
    sbom_digest:str
    ticket:str
    def digest(self):
        if not isinstance(self.repository,str) or not NAME.fullmatch(self.repository):raise SupplyError("repo")
        for x in (self.commit_sha,self.artifact_sha256,self.sbom_digest):
            if not isinstance(x,str) or not HEX.fullmatch(x):raise SupplyError("digest")
        if not isinstance(self.ticket,str) or not NAME.fullmatch(self.ticket):raise SupplyError("ticket")
        return sha(asdict(self))
def gate(plan,approval=None,now=0,dry_run=True):
    if type(now) is not int or now<0 or type(dry_run) is not bool:raise SupplyError("mode")
    d=plan.digest();a=approval or {}
    if not isinstance(a,dict):raise SupplyError("approval")
    valid=(a.get("approved") is True and isinstance(a.get("digest"),str) and hmac.compare_digest(a["digest"],d)
           and isinstance(a.get("owner"),str) and bool(a["owner"].strip())
           and isinstance(a.get("approver"),str) and bool(a["approver"].strip()) and a["owner"]!=a["approver"]
           and type(a.get("expires_at")) is int and a["expires_at"]>now and a.get("rollback_tested") is True)
    return {"fingerprint":d,"decision":"advisory-only" if valid else "hold","dry_run":dry_run,
            "signed":False,"provenance_verified":False,"mutations":0,"network_calls":0}
def samples():
    return [Dependency("requests","2.32.3","a"*64,True,"pypi"),
            Dependency("urllib3","2.2.3","b"*64,False,"pypi"),
            Dependency("PyYAML","6.0.2","c"*64,True,"pypi")]
def demo(partial=False):
    rows=paginate(Pager(samples(),1).fetch)
    report=sbom(rows,not partial)
    risk=assess(rows,[Finding("urllib3","2.2.3","DEMO-2026-1","high")],not partial)
    plan=ReleasePlan("python-sre","1"*64,"2"*64,report["digest"],"INC-105")
    return {"mode":"offline","sbom":report,"risk":risk,"release":gate(plan),
            "actual_vulnerability_scan":False,"cryptographic_signatures_verified":False,"network_calls":0,"mutations":0}
def main(argv=None):
    p=argparse.ArgumentParser(description="Offline Python supply chain risk lab")
    p.add_argument("--dry-run",action="store_true");p.add_argument("--partial",action="store_true")
    a=p.parse_args(argv);print(json.dumps(demo(a.partial),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
