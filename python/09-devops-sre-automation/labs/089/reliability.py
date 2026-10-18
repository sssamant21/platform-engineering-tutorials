"""Deterministic, read-only SLI/SLO, burn-rate and operational readiness lab."""
from __future__ import annotations
import argparse
from dataclasses import asdict,dataclass
from datetime import datetime,timezone
import json,math

class ReliabilityError(ValueError):pass

@dataclass(frozen=True)
class Event:
    at:float
    good:bool
    eligible:bool=True
    latency_ms:float=0

    def validate(self):
        if not math.isfinite(self.at) or not math.isfinite(self.latency_ms) or self.latency_ms<0:
            raise ReliabilityError("invalid event timestamp/latency")
        if type(self.good) is not bool or type(self.eligible) is not bool:
            raise ReliabilityError("invalid event classification")

@dataclass(frozen=True)
class Objective:
    target:float=0.999
    latency_threshold_ms:float=500
    min_events:int=20

    def validate(self):
        if not math.isfinite(self.target) or not 0<self.target<1:
            raise ReliabilityError("target must be between 0 and 1")
        if not math.isfinite(self.latency_threshold_ms) or self.latency_threshold_ms<=0:
            raise ReliabilityError("invalid latency threshold")
        if type(self.min_events) is not int or self.min_events<1:
            raise ReliabilityError("invalid minimum events")

def window(events:list[Event],start:float,end:float,objective:Objective)->dict:
    objective.validate()
    if not all(math.isfinite(t) for t in (start,end)) or start>=end:
        raise ReliabilityError("invalid window")
    rows=[]
    seen=set()
    for e in events:
        e.validate()
        if start<=e.at<end and e.eligible:
            # Events in this lab are assumed unique; a real pipeline needs stable event IDs.
            rows.append(e)
    n=len(rows)
    if n==0:
        return {"total":0,"good":0,"bad":0,"availability":None,"latency_sli":None,
                "remaining_budget":None,"budget_fraction":None,"burn_rate":None,"sufficient":False}
    good=sum(e.good for e in rows)
    fast=sum(e.good and e.latency_ms<=objective.latency_threshold_ms for e in rows)
    bad=n-good
    allowed=n*(1-objective.target)
    return {"total":n,"good":good,"bad":bad,"availability":good/n,
            "latency_sli":fast/n,"remaining_budget":allowed-bad,
            "budget_fraction":(allowed-bad)/allowed,
            "burn_rate":(bad/n)/(1-objective.target),
            "sufficient":n>=objective.min_events}

def multiwindow_burn(events:list[Event],now:float,objective:Objective,
                     short_seconds:float=300,long_seconds:float=3600,
                     threshold:float=14.4)->dict:
    if not all(math.isfinite(v) and v>0 for v in (short_seconds,long_seconds,threshold)):
        raise ReliabilityError("invalid burn policy")
    if short_seconds>=long_seconds:raise ReliabilityError("short window must be shorter")
    short=window(events,now-short_seconds,now,objective)
    long=window(events,now-long_seconds,now,objective)
    active=(short["sufficient"] and long["sufficient"] and
            short["burn_rate"]>=threshold and long["burn_rate"]>=threshold)
    return {"active":bool(active),"short":short,"long":long,"threshold":threshold}

REQUIRED_CHECKS=("telemetry_fresh","rollback_tested","owner_assigned",
                 "paging_route_tested","backup_restore_tested","capacity_reviewed")

def readiness(checks:dict[str,bool],burn:dict,*,open_sev1:bool=False)->dict:
    if any(type(checks.get(key)) is not bool for key in REQUIRED_CHECKS):
        return {"ready":False,"reasons":["missing-or-invalid-readiness-evidence"]}
    reasons=[key for key in REQUIRED_CHECKS if not checks[key]]
    if type(open_sev1) is not bool:raise ReliabilityError("invalid incident flag")
    if open_sev1:reasons.append("active-sev1")
    if not isinstance(burn,dict) or type(burn.get("active")) is not bool:
        reasons.append("missing-burn-evidence")
    elif burn["active"]:reasons.append("slo-fast-burn")
    if not reasons and (not burn["short"]["sufficient"] or not burn["long"]["sufficient"]):
        reasons.append("insufficient-sli-samples")
    return {"ready":not reasons,"reasons":reasons}

def fake_events(now=3600.0,count=100,failures=0):
    if not 0<=failures<=count:raise ReliabilityError("invalid fixture")
    return [Event(now-200+(i*1.0),i>=failures,True,150) for i in range(count)]

def main(argv=None):
    parser=argparse.ArgumentParser(description="Offline reliability and release-readiness evaluator")
    parser.add_argument("--dry-run",action="store_true")
    parser.add_argument("--failures",type=int,default=5)
    parser.add_argument("--target",type=float,default=0.99)
    args=parser.parse_args(argv)
    if args.dry_run:
        print(json.dumps({"dry_run":True,"network_calls":0,"mutations":0}))
        return 0
    try:
        obj=Objective(target=args.target)
        obj.validate()
        events=fake_events(failures=args.failures)
        burn=multiwindow_burn(events,3600,obj,threshold=2)
        checks={name:True for name in REQUIRED_CHECKS}
        gate=readiness(checks,burn)
    except ReliabilityError:
        print(json.dumps({"status":"invalid-input"}))
        return 2
    print(json.dumps({"generated_at":datetime.now(timezone.utc).isoformat(),
                      "mode":"offline-synthetic","burn":burn,"release_gate":gate},
                     sort_keys=True))
    return 0
if __name__=="__main__":raise SystemExit(main())
