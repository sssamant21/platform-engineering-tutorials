"""Offline deterministic resilience simulator. No sleeps, network, or production faults."""
from __future__ import annotations
from dataclasses import dataclass
import argparse,json,math,random
class ResilienceError(ValueError):pass
def positive(x,name,allow_zero=False):
    if type(x) not in (int,float) or not math.isfinite(x) or (x<0 if allow_zero else x<=0):raise ResilienceError(name)
    return x
def backoff(attempt,base_ms=100,cap_ms=5000,jitter=0,seed=1):
    if type(attempt) is not int or not 0<=attempt<=32:raise ResilienceError("attempt")
    positive(base_ms,"base");positive(cap_ms,"cap")
    if type(jitter) not in (int,float) or not math.isfinite(jitter) or not 0<=jitter<=1:raise ResilienceError("jitter")
    raw=min(float(cap_ms),float(base_ms)*2**attempt)
    return raw*(1-jitter*random.Random(seed+attempt).random())
def retry_plan(failures,max_attempts=3,idempotent=True,deadline_ms=2000,base_ms=100):
    if type(failures) is not int or failures<0:raise ResilienceError("failures")
    if type(max_attempts) is not int or not 1<=max_attempts<=20:raise ResilienceError("attempts")
    if type(idempotent) is not bool:raise ResilienceError("idempotent")
    positive(deadline_ms,"deadline");positive(base_ms,"base")
    if not idempotent:return {"status":"blocked-non-idempotent","attempts":0,"delay_ms":0,"mutations":0}
    elapsed=0.;used=0
    for i in range(max_attempts):
        used+=1
        if i>=failures:return {"status":"success","attempts":used,"delay_ms":elapsed,"mutations":0}
        if i==max_attempts-1:break
        delay=backoff(i,base_ms,min(deadline_ms,5000))
        if elapsed+delay>=deadline_ms:return {"status":"deadline","attempts":used,"delay_ms":elapsed,"mutations":0}
        elapsed+=delay
    return {"status":"exhausted","attempts":used,"delay_ms":elapsed,"mutations":0}
@dataclass
class Breaker:
    threshold:int=3
    reset_after:int=10
    state:str="closed"
    failures:int=0
    opened_at:int|None=None
    def __post_init__(self):
        if type(self.threshold) is not int or self.threshold<1:raise ResilienceError("threshold")
        if type(self.reset_after) is not int or self.reset_after<1:raise ResilienceError("reset")
    def allow(self,now):
        if type(now) is not int or now<0:raise ResilienceError("time")
        if self.state=="open" and self.opened_at is not None and now-self.opened_at>=self.reset_after:self.state="half-open"
        return self.state!="open"
    def record(self,success,now):
        if type(success) is not bool:raise ResilienceError("success")
        if not self.allow(now):return "rejected"
        if success:self.state="closed";self.failures=0;self.opened_at=None
        else:
            self.failures+=1
            if self.state=="half-open" or self.failures>=self.threshold:self.state="open";self.opened_at=now
        return self.state
def bulkhead(arrivals,active_limit,queue_limit):
    if any(type(x) is not int or x<0 for x in (arrivals,active_limit,queue_limit)) or active_limit<1:raise ResilienceError("capacity")
    active=min(arrivals,active_limit);queued=min(max(0,arrivals-active),queue_limit)
    return {"active":active,"queued":queued,"rejected":arrivals-active-queued}
def timeout_budget(total_ms,connect_ms,read_ms,retries=0):
    for k,x in (("total",total_ms),("connect",connect_ms),("read",read_ms)):positive(x,k)
    if type(retries) is not int or not 0<=retries<=10:raise ResilienceError("retries")
    return {"fits":(connect_ms+read_ms)*(retries+1)<=total_ms,"budget_ms":total_ms,"worst_case_ms":(connect_ms+read_ms)*(retries+1)}
def chaos_gate(environment,approved,rollback_ready,healthy,error_budget_remaining,blast_radius_pct):
    if environment not in {"lab","staging","production"}:raise ResilienceError("environment")
    if any(type(x) is not bool for x in (approved,rollback_ready,healthy)):raise ResilienceError("flags")
    positive(error_budget_remaining,"budget",True)
    if type(blast_radius_pct) not in (int,float) or not math.isfinite(blast_radius_pct) or not 0<blast_radius_pct<=100:raise ResilienceError("blast radius")
    permitted=environment in {"lab","staging"} and approved and rollback_ready and healthy and error_budget_remaining>0 and blast_radius_pct<=5
    return {"decision":"simulation-authorized" if permitted else "hold","environment":environment,"faults_injected":0,"mutations":0}
def sli(good,total,target=.999):
    if type(good) is not int or type(total) is not int or not 0<=good<=total:raise ResilienceError("events")
    if type(target) not in (int,float) or not math.isfinite(target) or not 0<target<1:raise ResilienceError("target")
    allowed=total*(1-target);bad=total-good
    return {"availability":None if total==0 else good/total,"remaining_bad_events":allowed-bad,
            "status":"unknown" if total==0 else "breached" if bad>allowed else "within-budget"}
def scenario(name,failures,max_attempts,capacity,queue,arrivals):
    if not isinstance(name,str) or not name or len(name)>80:raise ResilienceError("name")
    return {"name":name,"retry":retry_plan(failures,max_attempts),"bulkhead":bulkhead(arrivals,capacity,queue),
            "action":"advisory-only","network_calls":0,"mutations":0}
def demo():
    breaker=Breaker()
    history=[breaker.record(False,t) for t in (1,2,3)]
    return {"mode":"offline","backoff_ms":[backoff(i,100,1000,.2) for i in range(4)],
            "retry":retry_plan(2,4),"breaker_history":history,"breaker_open":breaker.state=="open",
            "bulkhead":bulkhead(20,5,3),"timeout":timeout_budget(1000,100,200,2),
            "slo":sli(998,1000,.999),"chaos":chaos_gate("staging",True,True,True,50,2),
            "incident":scenario("postgres-pool-exhaustion",3,3,5,3,20),"mutations":0,"network_calls":0}
def main(argv=None):
    p=argparse.ArgumentParser(description="Offline resilience and chaos policy lab")
    p.add_argument("--dry-run",action="store_true")
    a=p.parse_args(argv);print(json.dumps(demo(),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
