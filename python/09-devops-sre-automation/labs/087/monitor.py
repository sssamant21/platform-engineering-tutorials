"""Host monitoring and deterministic in-process alert deduplication."""
from dataclasses import dataclass,asdict
from collections import deque
import argparse,json,math,time

@dataclass(frozen=True)
class Sample:
    cpu:float
    memory:float
    disk:float
    timestamp:float
    def validate(self):
        if any(not math.isfinite(v) or not 0<=v<=100 for v in (self.cpu,self.memory,self.disk)):
            raise ValueError("invalid percentage")
        if not math.isfinite(self.timestamp):raise ValueError("invalid timestamp")

class Sampler:
    def __init__(self,psutil):self.psutil=psutil
    def sample(self,path="/",clock=time.time):
        p=self.psutil
        result=Sample(float(p.cpu_percent(interval=.1)),float(p.virtual_memory().percent),
                      float(p.disk_usage(path).percent),clock())
        result.validate()
        return result

@dataclass(frozen=True)
class Rule:
    warning:float=75
    critical:float=90
    clear:float=70
    def validate(self):
        if not 0<=self.clear<self.warning<self.critical<=100:
            raise ValueError("invalid thresholds")

class Alerts:
    """Per-process state only; use Alertmanager for durable production dedup."""
    def __init__(self,rules=None,cooldown=300):
        self.rules=rules or {name:Rule() for name in ("cpu","memory","disk")}
        for rule in self.rules.values():rule.validate()
        if not math.isfinite(cooldown) or cooldown<0:raise ValueError("invalid cooldown")
        self.cooldown=cooldown
        self.state={}
    def evaluate(self,sample):
        sample.validate()
        events=[]
        for name,rule in self.rules.items():
            value=getattr(sample,name)
            old,last=self.state.get(name,("ok",float("-inf")))
            level="critical" if value>=rule.critical else ("warning" if value>=rule.warning else (old if old!="ok" and value>rule.clear else "ok"))
            changed=level!=old
            if changed or (level!="ok" and sample.timestamp-last>=self.cooldown):
                events.append({"metric":name,"severity":level,"value":value,"timestamp":sample.timestamp,
                               "transition":"change" if changed else "repeat"})
                last=sample.timestamp
            self.state[name]=(level,last)
        return events

class SLO:
    def __init__(self,size=1000):
        if not 1<=size<=100000:raise ValueError("invalid window")
        self.events=deque(maxlen=size)
    def observe(self,success):
        if not isinstance(success,bool):raise TypeError("expected bool")
        self.events.append(success)
    def availability(self):
        return sum(self.events)/len(self.events) if self.events else None
    def budget(self,target):
        if not 0<target<1:raise ValueError("invalid target")
        if not self.events:return None
        allowed=len(self.events)*(1-target)
        return (allowed-(len(self.events)-sum(self.events)))/allowed

def prometheus_text(sample):
    sample.validate()
    output=[]
    for name in ("cpu","memory","disk"):
        metric="sre_host_"+name+"_usage_percent"
        output.extend(["# HELP "+metric+" Host utilization percent","# TYPE "+metric+" gauge",
                       metric+" "+str(getattr(sample,name))])
    return "\n".join(output)+"\n"

def main(argv=None):
    parser=argparse.ArgumentParser(description="Read-only host monitoring")
    parser.add_argument("--disk-path",default="/")
    parser.add_argument("--format",choices=("json","prometheus"),default="json")
    parser.add_argument("--dry-run",action="store_true")
    args=parser.parse_args(argv)
    if args.dry_run:
        print(json.dumps({"dry_run":True,"sampling_calls":0,"disk_path":args.disk_path}))
        return 0
    import psutil
    sample=Sampler(psutil).sample(args.disk_path)
    if args.format=="prometheus":
        print(prometheus_text(sample),end="")
    else:
        print(json.dumps({"sample":asdict(sample),"events":Alerts().evaluate(sample)},sort_keys=True))
    return 0
if __name__=="__main__":raise SystemExit(main())
