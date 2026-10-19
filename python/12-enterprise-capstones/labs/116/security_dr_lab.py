"""Offline security and disaster recovery acceptance simulator. No external writes."""
import argparse,hashlib,json,re
class PolicyError(ValueError):pass
def check(ok,why):
    if not ok:raise PolicyError(why)
def principal(subject,tenant,roles,expiry,now):
    check(all(isinstance(v,str) and re.fullmatch("[a-z][a-z0-9_-]{2,63}",v) for v in (subject,tenant)),"identity")
    check(type(roles) is list and bool(roles) and all(x in ("reader","operator","security","dr_admin") for x in roles),"roles")
    check(type(expiry) is int and type(now) is int and expiry>now,"expiry")
    return {"subject":subject,"tenant":tenant,"roles":roles}
ACL={"reader":{"read"},"operator":{"read","backup_plan"},"security":{"read","audit"},"dr_admin":{"read","backup_plan","restore_propose"}}
def allowed(p,tenant,action):
    check(type(p) is dict and set(p)=={"subject","tenant","roles"} and type(tenant) is str and action in {"read","backup_plan","audit","restore_propose"},"request")
    return p["tenant"]==tenant and any(action in ACL.get(r,set()) for r in p["roles"])
def secret(age,rotation,encrypted):
    check(type(age) is int and age>=0 and type(rotation) is int and rotation>0 and type(encrypted) is bool,"secret")
    return "pass" if encrypted and age<rotation else "hold"
def restore(age,rpo,duration,rto,checksum,encrypted,immutable,tested,approved):
    check(all(type(x) is int and x>=0 for x in (age,rpo,duration,rto)),"objectives")
    check(all(type(x) is bool for x in (checksum,encrypted,immutable,tested,approved)),"flags")
    failures=[]
    if age>rpo:failures.append("rpo")
    if duration>rto:failures.append("rto")
    for key,val in (("checksum",checksum),("encryption",encrypted),("immutability",immutable),("drill",tested),("approval",approved)):
        if not val:failures.append(key)
    return {"decision":"advisory-ready" if not failures else "hold","blockers":failures,"production_restores":0}
def supply(digest,signed,sbom,critical,approved):
    check(type(digest) is str and bool(re.fullmatch("[a-f0-9]{64}",digest)),"digest")
    check(all(type(x) is bool for x in (signed,sbom,approved)) and type(critical) is int and critical>=0,"supply")
    return {"decision":"advisory-ready" if signed and sbom and critical==0 and approved else "hold"}
def controls(c):
    check(type(c) is dict and bool(c) and all(type(k) is str and type(v) is bool for k,v in c.items()),"controls")
    failures=sorted(k for k,v in c.items() if not v)
    return {"status":"pass" if not failures else "hold","failed":failures}
def redact(d):
    check(type(d) is dict,"log")
    return {k:"[REDACTED]" if re.search("token|secret|password|patient|credential|key_material",str(k),re.I) else v for k,v in d.items()}
def demo(failure=False):
    p=principal("worker_001","tenant_001",["reader","operator"],1000,100)
    d={"mode":"offline","cross_tenant_allowed":allowed(p,"tenant_002","read"),"backup_plan_allowed":allowed(p,"tenant_001","backup_plan"),"secret":secret(10,30,True),"recovery":restore(180 if failure else 20,60,80,120,True,True,True,True,True),"supply":supply("a"*64,True,True,0,True),"controls":controls({"iam":True,"audit":True,"restore_drill":not failure}),"safe_log":redact({"patient_id":"123","status":"reviewed"}),"network_calls":0,"production_mutations":0}
    d["fingerprint"]=hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest()
    return d
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument("--dry-run",action="store_true");p.add_argument("--failure",action="store_true")
    a=p.parse_args(argv);print(json.dumps(demo(a.failure),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
