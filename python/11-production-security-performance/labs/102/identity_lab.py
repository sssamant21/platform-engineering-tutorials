"""Offline identity and authorization policy simulator; NOT a JWT signature verifier."""
from dataclasses import dataclass,asdict
import argparse,hashlib,json,re
class IdentityError(ValueError):pass
ID=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@-]{0,127}$")
ROLES={"viewer":{"read"},"operator":{"read","deploy","restart"},"dbre":{"read","db-diagnostics","db-failover"},"security":{"read","audit","approve"}}
SENSITIVE={"deploy","restart","db-failover"}
@dataclass(frozen=True)
class VerifiedPrincipal:
    subject:str
    tenant:str
    issuer:str
    audience:str
    roles:tuple[str,...]
    scopes:tuple[str,...]
    expires_at:int
    not_before:int
    token_id:str
    def validate(self,now,issuer,audience):
        if type(now) is not int or any(not isinstance(x,str) or not ID.fullmatch(x) for x in
            (self.subject,self.tenant,self.issuer,self.audience,self.token_id)):raise IdentityError("invalid identity")
        if self.issuer!=issuer or self.audience!=audience:raise IdentityError("issuer or audience")
        if type(self.expires_at) is not int or type(self.not_before) is not int or not self.not_before<=now<self.expires_at:
            raise IdentityError("token time")
        if not isinstance(self.roles,tuple) or not isinstance(self.scopes,tuple) or any(x not in ROLES for x in self.roles):
            raise IdentityError("role")
        if any(not isinstance(x,str) or not ID.fullmatch(x) for x in self.scopes):raise IdentityError("scope")
@dataclass(frozen=True)
class Resource:
    tenant:str
    name:str
    environment:str
    owner:str
    def validate(self):
        if any(not isinstance(x,str) or not ID.fullmatch(x) for x in asdict(self).values()):raise IdentityError("resource")
@dataclass(frozen=True)
class Request:
    action:str
    resource:Resource
    ticket:str|None=None
    def validate(self):
        self.resource.validate()
        if self.action not in set().union(*ROLES.values()):raise IdentityError("action")
        if self.ticket is not None and (not isinstance(self.ticket,str) or not ID.fullmatch(self.ticket)):raise IdentityError("ticket")
def fingerprint(p,r):
    payload={"subject":p.subject,"tenant":p.tenant,"action":r.action,"resource":asdict(r.resource),"ticket":r.ticket}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def authorize(p,r,*,now,issuer="https://issuer.example",audience="sre-api",approval=None,seen=None):
    if not isinstance(p,VerifiedPrincipal) or not isinstance(r,Request):raise IdentityError("types")
    p.validate(now,issuer,audience);r.validate()
    reason="allow"
    if p.tenant!=r.resource.tenant:reason="tenant-mismatch"
    elif r.action not in set().union(*(ROLES[role] for role in p.roles)):reason="rbac-deny"
    elif r.action not in p.scopes:reason="scope-deny"
    elif r.action in SENSITIVE and r.resource.environment=="prod":
        a=approval or {}
        if not isinstance(a,dict) or a.get("approved") is not True or a.get("digest")!=fingerprint(p,r) or not r.ticket:
            reason="approval-required"
        elif not isinstance(a.get("approver"),str) or not a["approver"] or a["approver"]==p.subject:
            reason="separation-of-duties"
        elif type(a.get("expires_at")) is not int or a["expires_at"]<=now or a.get("rollback_tested") is not True:
            reason="approval-expired-or-rollback"
    if reason=="allow" and r.action in SENSITIVE and seen is not None:
        if p.token_id in seen:reason="replay"
        else:seen.add(p.token_id)
    return {"allowed":reason=="allow","reason":reason,"subject_hash":hashlib.sha256(p.subject.encode()).hexdigest()[:12],
            "tenant":p.tenant,"action":r.action,"resource":r.resource.name,"policy":"v1","mutations":0,"network_calls":0}
def examples():
    p=VerifiedPrincipal("sre-oncall","tenant-a","https://issuer.example","sre-api",("operator",),("read","deploy"),200,100,"jti-101")
    r=Request("deploy",Resource("tenant-a","patient-api","prod","platform"),"INC-102")
    return p,r
def demo():
    p,r=examples()
    hold=authorize(p,r,now=150)
    approval={"approved":True,"digest":fingerprint(p,r),"approver":"security-oncall","expires_at":180,"rollback_tested":True}
    approved=authorize(p,r,now=150,approval=approval)
    return {"mode":"offline-post-verification","unapproved":hold,"approved_advisory":approved,
            "jwt_signature_verification":False,"mutations":0,"network_calls":0,"tokens_issued":0}
def main(argv=None):
    parser=argparse.ArgumentParser(description="Offline RBAC/ABAC lab")
    parser.add_argument("--dry-run",action="store_true");parser.parse_args(argv)
    print(json.dumps(demo(),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
