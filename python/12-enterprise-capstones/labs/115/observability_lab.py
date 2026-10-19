"""Chapter 115 offline incident/observability simulator. Python 3.11+ stdlib.
No network, exporters, production mutations, paging or credentials.
"""
from __future__ import annotations
from dataclasses import dataclass,field
import argparse,hashlib,json,math,re
class EvidenceError(ValueError):pass
def require(ok,why):
    if not ok:raise EvidenceError(why)
def percentile(samples,p):
    require(type(samples) is list and len(samples)>0 and all(type(v) in (int,float) and math.isfinite(v) and v>=0 for v in samples),"samples")
    require(type(p) in (int,float) and 0<=p<=100,"percentile")
    a=sorted(samples);x=(len(a)-1)*p/100;i=math.floor(x);return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(x-i)
def redact(record):
    require(type(record) is dict,"log")
    secret=re.compile(r"(token|secret|password|authorization|api_key|patient|email)",re.I)
    return {str(k):"[REDACTED]" if secret.search(str(k)) else v for k,v in record.items()}
def validate_trace(spans):
    require(type(spans) is list and len(spans)>0,"spans")
    ids=set();parents={};names=set()
    for s in spans:
        require(type(s) is dict and set(s)=={"id","parent","service","duration_ms","status"},"span_schema")
        require(type(s["id"]) is str and bool(re.fullmatch(r"[a-z0-9_-]{3,40}",s["id"])) and s["id"] not in ids,"span_id")
        require(s["parent"] is None or type(s["parent"]) is str,"parent")
        require(type(s["service"]) is str and bool(s["service"]),"service")
        require(type(s["duration_ms"]) in (int,float) and math.isfinite(s["duration_ms"]) and s["duration_ms"]>=0,"duration")
        require(s["status"] in ("ok","error"),"status")
        ids.add(s["id"]);parents[s["id"]]=s["parent"];names.add(s["service"])
    require(all(parent is None or parent in ids for parent in parents.values()),"missing_parent")
    roots=[k for k,v in parents.items() if v is None]
    require(len(roots)==1,"root")
    for ident in ids:
        seen=set();cur=ident
        while cur is not None:
            require(cur not in seen,"trace_cycle");seen.add(cur);cur=parents[cur]
    return {"root":roots[0],"spans":len(ids),"services":sorted(names),"errors":sum(s["status"]=="error" for s in spans)}
def sli(good,total,target=.999):
    require(type(good) is int and type(total) is int and 0<=good<=total,"counts")
    require(type(target) in (int,float) and math.isfinite(target) and 0<target<1,"target")
    if total==0:return {"status":"unknown","ratio":None,"budget_events":None,"remaining_events":None}
    ratio=good/total;budget=total*(1-target)
    return {"status":"pass" if ratio>=target else "breach","ratio":ratio,"budget_events":budget,"remaining_events":budget-(total-good)}
def burn(bad,total,target=.999):
    require(type(bad) is int and type(total) is int and 0<=bad<=total,"counts")
    require(type(target) in (int,float) and math.isfinite(target) and 0<target<1,"target")
    return None if total==0 else (bad/total)/(1-target)
def multiwindow(short_bad,short_total,long_bad,long_total,target=.999,threshold=14.4):
    require(type(threshold) in (int,float) and math.isfinite(threshold) and threshold>0,"threshold")
    a=burn(short_bad,short_total,target);b=burn(long_bad,long_total,target)
    return {"status":"unknown" if a is None or b is None else "page" if a>=threshold and b>=threshold else "observe","short_burn":a,"long_burn":b}
def red(requests,errors,latencies):
    require(type(requests) is int and type(errors) is int and 0<=errors<=requests,"requests")
    require(type(latencies) is list and len(latencies)==requests,"latency_count")
    return {"requests":requests,"errors":errors,"error_ratio":None if requests==0 else errors/requests,"p99_ms":None if requests==0 else percentile(latencies,99)}
def use(utilization,saturation,errors):
    require(all(type(x) in (int,float) and math.isfinite(x) and x>=0 for x in (utilization,saturation,errors)),"use")
    require(utilization<=1,"utilization")
    return {"utilization":utilization,"saturation":saturation,"errors":errors}
def correlate(signals):
    require(type(signals) is list,"signals")
    groups={}
    for s in signals:
        require(type(s) is dict and set(s)=={"incident","service","kind","severity"},"signal_schema")
        require(all(type(s[k]) is str and bool(s[k]) for k in s),"signal")
        require(s["kind"] in ("log","metric","trace","change"),"kind")
        require(s["severity"] in ("info","warning","critical"),"severity")
        groups.setdefault(s["incident"],[]).append(s)
    return {k:{"count":len(v),"services":sorted({x["service"] for x in v}),"kinds":sorted({x["kind"] for x in v}),"critical":sum(x["severity"]=="critical" for x in v)} for k,v in sorted(groups.items())}
def gate(slo_status,trace_coverage,rollback,owner,approved):
    require(slo_status in ("pass","breach","unknown"),"slo_status")
    require(type(trace_coverage) in (int,float) and math.isfinite(trace_coverage) and 0<=trace_coverage<=1,"coverage")
    require(all(type(x) is bool for x in (rollback,owner,approved)),"gate_flags")
    blockers=[]
    if slo_status!="pass":blockers.append("slo_"+slo_status)
    if trace_coverage<.95:blockers.append("trace_coverage")
    if not rollback:blockers.append("rollback_missing")
    if not owner:blockers.append("owner_missing")
    if not approved:blockers.append("approval_missing")
    return {"decision":"advisory-ready" if not blockers else "hold","blockers":blockers}
def demo(partial=False):
    spans=[{"id":"root_001","parent":None,"service":"api","duration_ms":110,"status":"ok"},{"id":"db_001","parent":"root_001","service":"postgres","duration_ms":70,"status":"ok"},{"id":"kafka_001","parent":"root_001","service":"worker","duration_ms":20,"status":"ok"}]
    r={"mode":"offline","trace":validate_trace(spans),"red":red(4,0,[20,30,40,110]),"use":use(.7,2,0),"sli":sli(999,1000),"burn":multiwindow(1,1000,2,2000),"correlation":correlate([{"incident":"inc_001","service":"api","kind":"metric","severity":"warning"},{"incident":"inc_001","service":"postgres","kind":"trace","severity":"critical"}]),"safe_log":redact({"message":"timeout","authorization":"Bearer sample","patient_id":"private"}),"gate":gate("unknown" if partial else "pass",.6 if partial else 1,True,True,True),"network_calls":0,"production_mutations":0}
    r["fingerprint"]=hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest()
    return r
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument("--dry-run",action="store_true");p.add_argument("--partial",action="store_true");a=p.parse_args(argv)
    print(json.dumps(demo(a.partial),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
