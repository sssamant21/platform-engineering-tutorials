"""Offline three-cloud incident lab. Python 3.11+. No network or mutations."""
from dataclasses import dataclass
from collections import defaultdict
import argparse,hashlib,json,math

class LabError(ValueError):pass
@dataclass(frozen=True)
class Signal:
    provider:str
    scope:str
    service:str
    metric:str
    value:float
    timestamp:int
    severity:str
    trace_id:str=""
    def validate(self):
        if self.provider not in {"aws","azure","gcp"} or not all(isinstance(v,str) and v for v in (self.scope,self.service,self.metric)):
            raise LabError("invalid identity")
        if type(self.value) not in (int,float) or not math.isfinite(self.value) or self.value<0:
            raise LabError("invalid value")
        if type(self.timestamp) is not int or self.timestamp<0 or self.severity not in ("warning","critical"):
            raise LabError("invalid timestamp/severity")
        if self.trace_id and (len(self.trace_id)!=32 or any(c not in "0123456789abcdef" for c in self.trace_id.lower())):
            raise LabError("invalid trace id")

def normalize(raw,now,max_age=300):
    if type(now) is not int or type(max_age) is not int or max_age<0:raise LabError("invalid clock")
    result=[]
    for record in raw:
        if not isinstance(record,dict):raise LabError("invalid record")
        try:s=Signal(**record)
        except (TypeError,ValueError) as exc:raise LabError("malformed signal") from exc
        s.validate()
        if s.timestamp>now or now-s.timestamp>max_age:raise LabError("stale/future signal")
        result.append(s)
    return result

def paginate(fetch,max_pages=20,max_items=1000):
    if not 1<=max_pages<=100 or not 1<=max_items<=100000:raise LabError("invalid budget")
    token=None;seen=set();items=[]
    for _ in range(max_pages):
        page=fetch(token)
        if not isinstance(page,dict) or not isinstance(page.get("items"),list):raise LabError("malformed page")
        items.extend(page["items"])
        if len(items)>max_items:raise LabError("item budget exceeded")
        token=page.get("next")
        if not token:return items
        if not isinstance(token,str) or token in seen:raise LabError("pagination loop")
        seen.add(token)
    raise LabError("page budget exceeded")

def slo(good,total,target=.999):
    if any(type(x) not in (int,float) or not math.isfinite(x) for x in (good,total,target)) or not (0<=good<=total and total>0 and 0<target<1):
        raise LabError("invalid SLO")
    budget=total*(1-target);bad=total-good
    return {"availability":round(good/total,6),"target":target,"budget_events":round(budget,3),
            "bad_events":bad,"burn_ratio":round(bad/budget,3),"breached":good/total<target}

def correlate(signals,window_seconds=300):
    if type(window_seconds) is not int or window_seconds<=0:raise LabError("invalid window")
    groups=defaultdict(list)
    for s in signals:
        s.validate()
        groups[(s.service,s.timestamp//window_seconds)].append(s)
    incidents=[]
    for (service,bucket),members in sorted(groups.items()):
        unique={(s.provider,s.scope,s.metric,s.severity):s for s in members}
        severity="critical" if any(s.severity=="critical" for s in unique.values()) else "warning"
        incident_id=hashlib.sha256(f"{service}|{bucket}".encode()).hexdigest()[:16]
        incidents.append({"id":incident_id,"service":service,"bucket":bucket,"severity":severity,
                          "alerts":len(unique),"providers":sorted({s.provider for s in unique.values()}),
                          "trace_ids":sorted({s.trace_id for s in unique.values() if s.trace_id}),
                          "causality":"not-established"})
    return incidents

def plan(incident,action="investigate"):
    if action!="investigate" or not isinstance(incident,dict) or not incident.get("id"):
        raise LabError("unsafe plan")
    canonical=json.dumps({"incident":incident,"action":action},sort_keys=True,separators=(",",":"))
    return hashlib.sha256(canonical.encode()).hexdigest()

def gate(incident,approval=None,dry_run=True):
    digest=plan(incident);a=approval or {}
    allowed=(a.get("approved") is True and a.get("digest")==digest and
             a.get("rollback_tested") is True and isinstance(a.get("owner"),str) and bool(a["owner"].strip()))
    return {"digest":digest,"approved":allowed,"action":"advisory-only" if allowed else "hold",
            "dry_run":dry_run,"mutations":0,"network_calls":0}

class FakePager:
    def __init__(self,items,size=2):self.items=items;self.size=size
    def fetch(self,token):
        i=int(token or 0)
        return {"items":self.items[i:i+self.size],"next":str(i+self.size) if i+self.size<len(self.items) else None}

def demo():
    raw=[{"provider":p,"scope":scope,"service":"patient-api","metric":metric,"value":value,
          "timestamp":1000,"severity":severity,"trace_id":"a"*32}
         for p,scope,metric,value,severity in [
             ("aws","123456789012","latency_ms",2200,"critical"),
             ("azure","sub-staging","cpu_pct",91,"warning"),
             ("gcp","sre-staging-12345","errors",25,"critical")]]
    signals=normalize(paginate(FakePager(raw,1).fetch),1100)
    incidents=correlate(signals)
    return {"mode":"offline","signals":len(signals),"incidents":incidents,
            "slo":slo(9980,10000),"change":gate(incidents[0]),"mutations":0,"network_calls":0}

def main(argv=None):
    p=argparse.ArgumentParser(description="Offline multi-cloud incident lab")
    p.add_argument("--dry-run",action="store_true")
    p.parse_args(argv)
    print(json.dumps(demo(),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
