"""Offline Chapter 110 SRE/DBRE integrated readiness evaluator (stdlib only)."""
import argparse,hashlib,json,math,re
class LabError(ValueError):pass
def valid_number(x):
    return type(x) in (int,float) and math.isfinite(x) and x>=0
def identity(roles,required):
    if not isinstance(roles,list) or any(not isinstance(x,str) for x in roles) or not isinstance(required,str):raise LabError("identity")
    return {"allowed":required in roles,"least_privilege":len(set(roles))<=2}
def secrets(age_days,rotation_days=90):
    if type(age_days) is not int or age_days<0 or type(rotation_days) is not int or rotation_days<1:raise LabError("secrets")
    return {"rotation_due":age_days>=rotation_days,"secret_material_exported":False}
def compliance(states):
    if not isinstance(states,list) or any(x not in ("pass","fail","unknown") for x in states):raise LabError("controls")
    return {"status":"unknown" if not states or "unknown" in states else "fail" if "fail" in states else "pass","controls":len(states)}
def supply_chain(packages):
    if not isinstance(packages,list):raise LabError("packages")
    seen=set()
    for p in packages:
        if not isinstance(p,dict) or set(p)!={"name","version","sha256","trusted"}:raise LabError("package schema")
        if not isinstance(p["name"],str) or not re.fullmatch("[a-z][a-z0-9_-]{1,49}",p["name"]) or not isinstance(p["version"],str) or not re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}",p["version"]) or not isinstance(p["sha256"],str) or not re.fullmatch("[a-f0-9]{64}",p["sha256"]) or type(p["trusted"]) is not bool:raise LabError("package")
        if p["name"] in seen:raise LabError("duplicate")
        seen.add(p["name"])
    return {"status":"unknown" if not packages else "pass" if all(p["trusted"] for p in packages) else "fail","count":len(packages),"signature_verified":False}
def percentile(samples,p):
    if not isinstance(samples,list) or not samples or any(not valid_number(x) for x in samples) or not valid_number(p) or p>100:raise LabError("latencies")
    a=sorted(samples);idx=(len(a)-1)*p/100;lo=math.floor(idx);hi=math.ceil(idx)
    return a[lo]+(a[hi]-a[lo])*(idx-lo)
def performance(samples,limit=200):
    if not valid_number(limit) or limit==0:raise LabError("limit")
    return {"p50":percentile(samples,50),"p95":percentile(samples,95),"p99":percentile(samples,99),"pass":percentile(samples,99)<=limit}
def concurrency(arrivals,active,queue):
    if any(type(x) is not int or x<0 for x in (arrivals,active,queue)) or active<1:raise LabError("capacity")
    return {"inflight":min(arrivals,active),"queued":min(max(0,arrivals-active),queue),"rejected":max(0,arrivals-active-queue)}
def slo(good,total,target=.99):
    if any(type(x) is not int for x in (good,total)) or not 0<=good<=total or not valid_number(target) or not 0<target<1:raise LabError("slo")
    bad=total-good;budget=total*(1-target)
    return {"availability":None if total==0 else good/total,"remaining":budget-bad,"status":"unknown" if total==0 else "breached" if bad>budget else "pass"}
def retry(failures,attempts,idempotent):
    if type(failures) is not int or failures<0 or type(attempts) is not int or not 1<=attempts<=10 or type(idempotent) is not bool:raise LabError("retry")
    return {"status":"blocked" if not idempotent else "success" if failures<attempts else "exhausted","attempts":0 if not idempotent else min(attempts,failures+1)}
def redact(fields):
    if not isinstance(fields,dict):raise LabError("log")
    return {k:"[REDACTED]" if any(t in k.lower() for t in ("password","token","secret","credential","authorization")) else v for k,v in fields.items()}
def release(ident,secret,controls,packages,perf,slo_result,approved):
    if type(approved) is not bool:raise LabError("approval")
    blockers=[]
    if not ident["allowed"] or not ident["least_privilege"]:blockers.append("identity")
    if secret["rotation_due"]:blockers.append("secret-rotation")
    if controls["status"]!="pass":blockers.append("compliance")
    if packages["status"]!="pass":blockers.append("supply-chain")
    if not perf["pass"]:blockers.append("latency")
    if slo_result["status"]!="pass":blockers.append("slo")
    if not approved:blockers.append("approval")
    return {"decision":"advisory-ready" if not blockers else "hold","blockers":blockers,"deployments":0}
def demo(partial=False):
    ident=identity(["read"],"read");secret=secrets(30)
    controls=compliance(["pass","unknown" if partial else "pass"])
    packages=supply_chain([{"name":"psycopg","version":"3.2.1","sha256":"a"*64,"trusted":True}])
    perf=performance([10,20,30,40,50]);s=slo(1000,1000)
    out={"mode":"offline","identity":ident,"secrets":secret,"compliance":controls,"supply_chain":packages,
         "performance":perf,"concurrency":concurrency(20,5,3),"slo":s,"retry":retry(1,3,True),
         "log":redact({"token":"demo","service":"api"}),"release":release(ident,secret,controls,packages,perf,s,True),
         "network_calls":0,"mutations":0}
    out["sha256"]=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return out
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument("--dry-run",action="store_true");p.add_argument("--partial",action="store_true")
    args=p.parse_args(argv);print(json.dumps(demo(args.partial),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
