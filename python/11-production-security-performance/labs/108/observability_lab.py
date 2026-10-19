"""Offline Python SRE observability lab: synthetic telemetry, no exports or network."""
from __future__ import annotations
from dataclasses import dataclass,asdict
import argparse,hashlib,json,math,re
class TelemetryError(ValueError):pass
TRACE=re.compile(r"^[0-9a-f]{32}$");SPAN=re.compile(r"^[0-9a-f]{16}$")
SAFE_KEY=re.compile(r"^[a-z][a-z0-9_]{0,39}$")
SENSITIVE=("password","secret","token","authorization","credential","api_key")
@dataclass(frozen=True)
class Span:
    trace_id:str
    span_id:str
    parent_span_id:str|None
    service:str
    operation:str
    duration_ms:float
    status:str
    def validate(self):
        if not isinstance(self.trace_id,str) or not TRACE.fullmatch(self.trace_id):raise TelemetryError("trace id")
        if not isinstance(self.span_id,str) or not SPAN.fullmatch(self.span_id):raise TelemetryError("span id")
        if self.parent_span_id is not None and (not isinstance(self.parent_span_id,str) or not SPAN.fullmatch(self.parent_span_id)):raise TelemetryError("parent")
        if self.parent_span_id==self.span_id:raise TelemetryError("self parent")
        if not isinstance(self.service,str) or not SAFE_KEY.fullmatch(self.service):raise TelemetryError("service")
        if not isinstance(self.operation,str) or not SAFE_KEY.fullmatch(self.operation):raise TelemetryError("operation")
        if type(self.duration_ms) not in (int,float) or not math.isfinite(self.duration_ms) or self.duration_ms<0:raise TelemetryError("duration")
        if self.status not in {"ok","error"}:raise TelemetryError("status")
def traces(spans):
    seen={};roots=0
    for s in spans:
        if not isinstance(s,Span):raise TelemetryError("span")
        s.validate()
        key=(s.trace_id,s.span_id)
        if key in seen:raise TelemetryError("duplicate span")
        seen[key]=s
    for s in seen.values():
        if s.parent_span_id is None:roots+=1
        elif (s.trace_id,s.parent_span_id) not in seen:raise TelemetryError("missing parent")
    for s in seen.values():
        visited=set();current=s
        while current.parent_span_id is not None:
            key=(current.trace_id,current.span_id)
            if key in visited:raise TelemetryError("cycle")
            visited.add(key);current=seen[(current.trace_id,current.parent_span_id)]
    return {"spans":len(seen),"roots":roots,"errors":sum(s.status=="error" for s in seen.values())}
def percentile(samples,p):
    if not isinstance(samples,(list,tuple)) or not samples:raise TelemetryError("samples")
    if any(type(x) not in (int,float) or not math.isfinite(x) or x<0 for x in samples):raise TelemetryError("samples")
    if type(p) not in (int,float) or not math.isfinite(p) or not 0<=p<=100:raise TelemetryError("percentile")
    a=sorted(samples);x=(len(a)-1)*p/100;lo=math.floor(x);hi=math.ceil(x)
    return a[lo]+(a[hi]-a[lo])*(x-lo)
def red(requests,errors,latencies,seconds):
    if type(requests) is not int or requests<0 or type(errors) is not int or not 0<=errors<=requests:raise TelemetryError("counts")
    if type(seconds) not in (int,float) or not math.isfinite(seconds) or seconds<=0:raise TelemetryError("window")
    if len(latencies)!=requests:raise TelemetryError("sample coverage")
    if requests==0:return {"rate_per_s":0.0,"error_ratio":None,"p95_ms":None,"p99_ms":None,"coverage":"no-traffic"}
    return {"rate_per_s":requests/seconds,"error_ratio":errors/requests,"p95_ms":percentile(latencies,95),"p99_ms":percentile(latencies,99),"coverage":"complete"}
def use(utilization,saturation,errors):
    if any(type(x) not in (int,float) or not math.isfinite(x) or x<0 for x in (utilization,saturation,errors)):raise TelemetryError("use")
    if utilization>1 or errors>1:raise TelemetryError("use range")
    return {"utilization":utilization,"saturation":saturation,"error_ratio":errors}
def sli(good,total):
    if type(good) is not int or type(total) is not int or total<0 or not 0<=good<=total:raise TelemetryError("sli")
    return None if total==0 else good/total
def error_budget(total,target,good):
    if type(total) is not int or type(good) is not int or total<0 or not 0<=good<=total:raise TelemetryError("counts")
    if type(target) not in (int,float) or not math.isfinite(target) or not 0<target<1:raise TelemetryError("target")
    allowed=total*(1-target);bad=total-good
    return {"allowed_bad":allowed,"observed_bad":bad,"remaining":allowed-bad,
            "burn_ratio":None if allowed==0 else bad/allowed,"status":"no-traffic" if total==0 else "breached" if bad>allowed else "within-budget"}
def burn_rate(short_bad,short_total,long_bad,long_total,target):
    for bad,total in ((short_bad,short_total),(long_bad,long_total)):
        if type(bad) is not int or type(total) is not int or not 0<=bad<=total:raise TelemetryError("burn counts")
    if type(target) not in (int,float) or not math.isfinite(target) or not 0<target<1:raise TelemetryError("target")
    if not short_total or not long_total:return {"short":None,"long":None,"status":"insufficient-data"}
    b=1-target;short=(short_bad/short_total)/b;long=(long_bad/long_total)/b
    return {"short":short,"long":long,"status":"investigate" if short>=14.4 and long>=14.4 else "observe"}
def sanitize(fields):
    if not isinstance(fields,dict):raise TelemetryError("fields")
    result={}
    for k,v in fields.items():
        if not isinstance(k,str) or not SAFE_KEY.fullmatch(k):raise TelemetryError("key")
        if any(s in k for s in SENSITIVE):result[k]="[REDACTED]"
        elif type(v) in (str,int,float,bool) or v is None:
            if type(v) is float and not math.isfinite(v):raise TelemetryError("value")
            result[k]=v if not isinstance(v,str) else v[:200]
        else:raise TelemetryError("value")
    return result
def log_event(service,level,message,fields):
    if not isinstance(service,str) or not SAFE_KEY.fullmatch(service):raise TelemetryError("service")
    if level not in {"INFO","WARN","ERROR"}:raise TelemetryError("level")
    if not isinstance(message,str) or len(message)>200:raise TelemetryError("message")
    return {"service":service,"level":level,"message":message,"attributes":sanitize(fields)}
def fingerprint(data):return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def incident(report,budget,complete=True):
    if type(complete) is not bool:raise TelemetryError("coverage")
    if not complete:return {"status":"unknown","action":"investigate-only","mutations":0}
    if report["error_ratio"] is None:return {"status":"insufficient-data","action":"investigate-only","mutations":0}
    return {"status":"page" if budget["status"]=="breached" else "observe","action":"investigate-only","mutations":0}
def demo(partial=False):
    t="a"*32
    spans=[Span(t,"1"*16,None,"api","request",150,"error"),Span(t,"2"*16,"1"*16,"postgres","query",120,"error")]
    r=red(5,1,[10,20,30,50,150],60);b=error_budget(5,.99,4)
    report={"mode":"offline","traces":traces(spans),"red":r,"use":use(.8,3,.2),"slo":b,
            "burn":burn_rate(2,100,4,1000,.99),"log":log_event("api","ERROR","db failure",{"token":"example","trace_id":t}),
            "incident":incident(r,b,not partial),"mutations":0,"network_calls":0}
    report["report_sha256"]=fingerprint(report)
    return report
def main(argv=None):
    p=argparse.ArgumentParser(description="Offline observability lab")
    p.add_argument("--dry-run",action="store_true");p.add_argument("--partial",action="store_true")
    a=p.parse_args(argv);print(json.dumps(demo(a.partial),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
