"""Chapter 101: offline secure SRE operations reference, Python 3.11+."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import argparse, hashlib, hmac, ipaddress, json, re
from pathlib import PurePosixPath

class SecurityError(ValueError): pass
ENV={"dev","staging","prod"}
ACTIONS={"read-inventory","review-policy","review-incident"}
IDENT=re.compile(r"^[a-z][a-z0-9_-]{1,62}$")
SHA256=re.compile(r"^[a-f0-9]{64}$")

def validate_request(raw:dict)->dict:
    if not isinstance(raw,dict) or set(raw)!={"service","environment","limit","request_id"}:
        raise SecurityError("invalid request schema")
    service,env,limit,request_id=(raw[k] for k in ("service","environment","limit","request_id"))
    if not isinstance(service,str) or not IDENT.fullmatch(service):raise SecurityError("invalid service")
    if env not in ENV:raise SecurityError("invalid environment")
    if type(limit) is not int or not 1<=limit<=100:raise SecurityError("invalid limit")
    if not isinstance(request_id,str) or not IDENT.fullmatch(request_id):raise SecurityError("invalid request id")
    return dict(raw)

def authorize(principal:dict,action:str,environment:str)->bool:
    if not isinstance(principal,dict) or set(principal)!={"subject","roles","environments"}:return False
    if not isinstance(principal["subject"],str) or not IDENT.fullmatch(principal["subject"]):return False
    roles=principal["roles"];envs=principal["environments"]
    if not isinstance(roles,list) or not isinstance(envs,list) or not all(isinstance(x,str) for x in roles+envs):return False
    if action not in ACTIONS or environment not in ENV or environment not in envs:return False
    permitted={"viewer":{"read-inventory"},"auditor":{"review-policy","review-incident"}}
    return any(action in permitted.get(role,set()) for role in roles)

def safe_workspace_path(name:str)->str:
    if not isinstance(name,str) or len(name)>120 or not name or "\\" in name or "%" in name:raise SecurityError("unsafe path")
    p=PurePosixPath(name)
    if p.is_absolute() or any(part in (".","..") for part in name.split("/")) or not all(IDENT.fullmatch(part) for part in p.parts):
        raise SecurityError("unsafe path")
    return str(p)
# For real filesystem access, use directory file descriptors and O_NOFOLLOW; this lexical check is not symlink protection.

def validate_endpoint(host:str)->str:
    if not isinstance(host,str):raise SecurityError("host")
    try:ip=ipaddress.ip_address(host)
    except ValueError as exc:raise SecurityError("IP literal required") from exc
    if not ip.is_global:raise SecurityError("nonpublic address forbidden")
    return str(ip)
# DNS and HTTP are intentionally not implemented; prevent SSRF by enforcing destination at connect time.

def redact(obj):
    sensitive={"password","secret","token","authorization","api_key","private_key"}
    if isinstance(obj,dict):
        return {k:("***REDACTED***" if isinstance(k,str) and k.lower() in sensitive else redact(v)) for k,v in obj.items()}
    if isinstance(obj,list):return [redact(x) for x in obj]
    return obj

def verify_digest(data:bytes,expected:str)->bool:
    if not isinstance(data,bytes) or not isinstance(expected,str) or not SHA256.fullmatch(expected):raise SecurityError("digest")
    return hmac.compare_digest(hashlib.sha256(data).hexdigest(),expected)
# A digest checks integrity against a trusted expected value; it does not authenticate an untrusted manifest.

@dataclass(frozen=True)
class Dependency:
    name:str
    version:str
    sha256:str
    approved:bool
    def validate(self):
        if not IDENT.fullmatch(self.name) or not re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}",self.version):raise SecurityError("dependency")
        if not SHA256.fullmatch(self.sha256) or type(self.approved) is not bool:raise SecurityError("dependency metadata")

def audit_event(subject:str,action:str,environment:str,decision:str,request_id:str)->dict:
    if not isinstance(subject,str) or not IDENT.fullmatch(subject):raise SecurityError("subject")
    if action not in ACTIONS or environment not in ENV or decision not in {"allow","deny"}:raise SecurityError("audit")
    if not isinstance(request_id,str) or not IDENT.fullmatch(request_id):raise SecurityError("request id")
    return {"subject":subject,"action":action,"environment":environment,"decision":decision,"request_id":request_id}

def advisory_plan(action:str,service:str,environment:str,ticket:str)->dict:
    if action not in ACTIONS or not isinstance(service,str) or not IDENT.fullmatch(service) or environment not in ENV or not isinstance(ticket,str) or not IDENT.fullmatch(ticket):
        raise SecurityError("unsafe plan")
    body={"action":action,"service":service,"environment":environment,"ticket":ticket}
    digest=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return {"body":body,"digest":digest}

def approval_gate(plan:dict,approval:dict|None=None,now:int=0)->dict:
    if type(now) is not int or now<0:raise SecurityError("clock")
    if not isinstance(plan,dict) or set(plan)!={"body","digest"} or not isinstance(plan["body"],dict):raise SecurityError("plan")
    body=plan["body"]
    if set(body)!={"action","service","environment","ticket"}:raise SecurityError("plan")
    canonical=advisory_plan(**body)
    if not hmac.compare_digest(canonical["digest"],str(plan["digest"])):raise SecurityError("tampered plan")
    a=approval or {}
    if not isinstance(a,dict):raise SecurityError("approval")
    valid=(a.get("approved") is True and isinstance(a.get("digest"),str) and
           hmac.compare_digest(a["digest"],plan["digest"]) and
           isinstance(a.get("owner"),str) and bool(a["owner"].strip()) and
           isinstance(a.get("approver"),str) and bool(a["approver"].strip()) and
           a["owner"]!=a["approver"] and a.get("rollback_tested") is True and
           type(a.get("expires_at")) is int and a["expires_at"]>now)
    return {"approved":valid,"decision":"advisory-only" if valid else "hold","mutations":0,"secret_reads":0,"network_calls":0}

def demo():
    request=validate_request({"service":"patient-api","environment":"staging","limit":20,"request_id":"req-101"})
    principal={"subject":"sre-viewer","roles":["viewer"],"environments":["staging"]}
    permitted=authorize(principal,"read-inventory",request["environment"])
    plan=advisory_plan("read-inventory",request["service"],request["environment"],"inc-101")
    dep=Dependency("example-lib","1.2.3","a"*64,True);dep.validate()
    return {"mode":"offline","authorized":permitted,
            "audit":audit_event(principal["subject"],"read-inventory","staging","allow" if permitted else "deny",request["request_id"]),
            "redacted":redact({"token":"synthetic","nested":{"password":"synthetic"}}),
            "dependency":{"name":dep.name,"version":dep.version,"approved":dep.approved},
            "plan":approval_gate(plan),"mutations":0,"secret_reads":0,"network_calls":0}
def main(argv=None):
    p=argparse.ArgumentParser(description="Offline production Python security lab")
    p.add_argument("--dry-run",action="store_true");p.parse_args(argv)
    print(json.dumps(demo(),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
