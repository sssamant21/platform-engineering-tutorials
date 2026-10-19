"""Chapter 119: offline, deterministic production-readiness acceptance and chaos planner.

No network, cloud calls, production writes, fault injection, or actual security scanning.
Python 3.11+ standard library.
"""
from __future__ import annotations
import argparse,hashlib,json,math,re
from dataclasses import dataclass

class ReadinessError(ValueError): pass
def require(ok:bool,reason:str)->None:
    if not ok: raise ReadinessError(reason)
def metric(value:float,name:str,positive:bool=False)->float:
    require(type(value) in (int,float) and math.isfinite(value) and (value>0 if positive else value>=0),name)
    return float(value)

WEIGHTS={"architecture":10,"deployment":10,"observability":15,"reliability":15,"security":15,"capacity":10,"disaster_recovery":15,"operations":10}
CRITICAL=("security","disaster_recovery","reliability","deployment")

@dataclass(frozen=True)
class Evidence:
    control:str
    passed:bool
    owner:str
    reference:str
    timestamp_utc:str
    def __post_init__(self):
        require(self.control in WEIGHTS,"control")
        require(type(self.passed) is bool,"passed")
        require(bool(re.fullmatch(r"[a-z][a-z0-9_-]{2,39}",self.owner)),"owner")
        require(bool(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_./:-]{2,119}",self.reference)),"reference")
        require(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",self.timestamp_utc)),"timestamp")

def review(items:list[Evidence],approved:bool,rollback_tested:bool)->dict:
    require(type(items) is list and all(type(e) is Evidence for e in items),"evidence")
    require(all(type(x) is bool for x in (approved,rollback_tested)),"approval")
    controls=[e.control for e in items]
    require(len(set(controls))==len(controls),"duplicate_control")
    present={e.control:e for e in items}
    missing=sorted(set(WEIGHTS)-set(present))
    failed=sorted(k for k,e in present.items() if not e.passed)
    score=sum(WEIGHTS[k] for k,e in present.items() if e.passed)
    blockers=[f"missing:{k}" for k in missing]+[f"failed:{k}" for k in failed if k in CRITICAL]
    if not approved:blockers.append("approval_missing")
    if not rollback_tested:blockers.append("rollback_not_tested")
    if score<90:blockers.append("score_below_90")
    return {"score":score,"max_score":100,"missing":missing,"failed":failed,"blockers":blockers,"decision":"advisory-ready" if not blockers else "hold","production_actions":0}

def slo(good:int,total:int,target:float,fast_errors:int,fast_total:int,slow_errors:int,slow_total:int)->dict:
    require(all(type(v) is int and v>=0 for v in (good,total,fast_errors,fast_total,slow_errors,slow_total)),"counts")
    require(good<=total and fast_errors<=fast_total and slow_errors<=slow_total,"counts")
    metric(target,"target",True);require(target<1,"target")
    if not total or not fast_total or not slow_total:
        return {"status":"unknown","availability":None,"remaining_budget":None,"fast_burn":None,"slow_burn":None}
    allowed=(1-target)*total
    spent=total-good
    return {"status":"pass" if good/total>=target else "breach","availability":good/total,"remaining_budget":max(0,allowed-spent),"fast_burn":(fast_errors/fast_total)/(1-target),"slow_burn":(slow_errors/slow_total)/(1-target)}

def load_gate(p99_ms:float,p99_limit_ms:float,error_rate:float,error_limit:float,cpu_util:float,memory_util:float,db_pool_util:float)->dict:
    for name,v in (("p99",p99_ms),("p99_limit",p99_limit_ms),("error_rate",error_rate),("error_limit",error_limit),("cpu",cpu_util),("memory",memory_util),("pool",db_pool_util)):metric(v,name,name=="p99_limit")
    require(all(v<=1 for v in (error_rate,error_limit,cpu_util,memory_util,db_pool_util)),"ratio")
    failed=[name for name,ok in (("latency",p99_ms<=p99_limit_ms),("errors",error_rate<=error_limit),("cpu",cpu_util<=.75),("memory",memory_util<=.8),("db_pool",db_pool_util<=.8)) if not ok]
    return {"decision":"pass" if not failed else "hold","failed":failed}

ALLOWED_FAULTS={"pod_kill","node_loss","region_outage","network_partition","db_latency","kafka_lag","cache_outage","telemetry_gap"}
def chaos_plan(fault:str,environment:str,blast_radius:int,abort_on_slo:bool,owner_approved:bool)->dict:
    require(fault in ALLOWED_FAULTS,"fault")
    require(environment in ("offline","staging"),"environment")
    require(type(blast_radius) is int and 0<=blast_radius<=10,"blast_radius")
    require(type(abort_on_slo) is bool and type(owner_approved) is bool,"flags")
    blockers=[]
    if blast_radius>2:blockers.append("blast_radius_exceeded")
    if not abort_on_slo:blockers.append("abort_guard_missing")
    if not owner_approved:blockers.append("owner_approval_missing")
    return {"decision":"plan-ready" if not blockers else "hold","blockers":blockers,"fault":fault,"environment":environment,"faults_injected":0}

def incident(severity:str,signals:list[str],owner:str,rollback:bool)->dict:
    require(severity in ("SEV1","SEV2","SEV3"),"severity")
    require(type(signals) is list and bool(signals) and all(s in ("api_5xx","p99","db_pool","kafka_lag","iops","security","telemetry","replication") for s in signals),"signals")
    require(type(owner) is str and bool(re.fullmatch("[a-z][a-z0-9_-]{2,39}",owner)),"owner")
    require(type(rollback) is bool,"rollback")
    return {"severity":severity,"owner":owner,"signals":sorted(set(signals)),"action":"escalate_and_contain" if severity=="SEV1" or not rollback else "investigate_and_rollback_if_verified","production_actions":0}

def sample(failure:bool=False)->dict:
    items=[Evidence(k,not(failure and k=="security"),"platform_team",f"evidence/{k}/20261019","2026-10-19T20:00:00Z") for k in WEIGHTS]
    report={"mode":"offline","review":review(items,True,True),"slo":slo(9997 if not failure else 9900,10000,.999,1 if not failure else 30,1000,2 if not failure else 50,2000),"load":load_gate(90 if not failure else 240,150,.0001,.001,.55,.6,.5),"chaos":chaos_plan("pod_kill","staging",1,True,True),"incident":incident("SEV2",["p99","db_pool"],"platform_team",True),"network_calls":0,"production_actions":0}
    report["fingerprint"]=hashlib.sha256(json.dumps(report,sort_keys=True).encode()).hexdigest()
    return report

def main(argv=None)->int:
    p=argparse.ArgumentParser();p.add_argument("--dry-run",action="store_true");p.add_argument("--failure",action="store_true")
    a=p.parse_args(argv);print(json.dumps(sample(a.failure),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
