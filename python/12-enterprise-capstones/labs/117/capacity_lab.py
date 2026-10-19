"""Chapter 117 offline capacity, SLO and FinOps simulator. No cloud calls."""
import argparse,json,math,hashlib
class CapacityError(ValueError):pass
def check(ok,msg):
    if not ok:raise CapacityError(msg)
def number(v,name,positive=False):
    check(type(v) in (int,float) and math.isfinite(v) and (v>0 if positive else v>=0),name)
    return v
def forecast(current,daily_growth,days,headroom=.25):
    for n,v in (("current",current),("growth",daily_growth),("days",days)):number(v,n)
    number(headroom,"headroom");check(headroom<1,"headroom")
    projected=current*(1+daily_growth)**days
    return {"projected":round(projected,4),"provisioned":round(projected/(1-headroom),4)}
def cpu_cores(rps,cpu_ms_per_request,target=.65):
    number(rps,"rps");number(cpu_ms_per_request,"cpu");number(target,"target",True);check(target<=1,"target")
    return math.ceil(rps*cpu_ms_per_request/1000/target*1000)/1000
def replicas(rps,per_pod_rps,min_replicas=2,max_replicas=30):
    number(rps,"rps");number(per_pod_rps,"per_pod",True)
    check(all(type(x) is int and x>=1 for x in (min_replicas,max_replicas)) and min_replicas<=max_replicas,"replica_bounds")
    needed=max(min_replicas,math.ceil(rps/per_pod_rps))
    return {"desired":min(needed,max_replicas),"needed":needed,"saturated":needed>max_replicas}
def storage(ingest_gb_day,retention_days,replicas_count,compression=.7,headroom=.25):
    for n,v in (("ingest",ingest_gb_day),("retention",retention_days),("replicas",replicas_count)):number(v,n)
    number(compression,"compression",True);number(headroom,"headroom");check(headroom<1,"headroom")
    raw=ingest_gb_day*retention_days*(1+replicas_count)*compression
    return {"used_gb":round(raw,3),"provisioned_gb":round(raw/(1-headroom),3)}
def iops(ops_sec,io_per_op,limit,target=.7):
    for n,v in (("ops",ops_sec),("io_per_op",io_per_op),("limit",limit)):number(v,n, n=="limit")
    number(target,"target",True);check(target<=1,"target")
    required=ops_sec*io_per_op
    return {"required":required,"utilization":required/limit,"safe":required<=limit*target}
def pool(replicas_count,pool_per_pod,max_connections,reserved):
    check(all(type(x) is int and x>=0 for x in (replicas_count,pool_per_pod,max_connections,reserved)),"pool")
    check(max_connections>reserved,"reserved")
    total=replicas_count*pool_per_pod
    return {"requested":total,"available":max_connections-reserved,"safe":total<=max_connections-reserved}
def cost(resources):
    check(type(resources) is list and bool(resources),"resources")
    by_team={};total=0
    for r in resources:
        check(type(r) is dict and set(r)=={"team","units","hours","usd_per_unit_hour"},"resource")
        check(type(r["team"]) is str and bool(r["team"]),"team")
        for name in ("units","hours","usd_per_unit_hour"):number(r[name],name)
        amount=r["units"]*r["hours"]*r["usd_per_unit_hour"]
        by_team[r["team"]]=by_team.get(r["team"],0)+amount;total+=amount
    return {"total_usd":round(total,2),"by_team_usd":{k:round(v,2) for k,v in sorted(by_team.items())}}
def loadtest(samples,errors,requests,latency_slo_ms,error_slo=.001):
    check(type(samples) is list and bool(samples) and all(type(v) in (int,float) and math.isfinite(v) and v>=0 for v in samples),"samples")
    check(type(errors) is int and type(requests) is int and 0<=errors<=requests and requests>0,"requests")
    number(latency_slo_ms,"latency",True);number(error_slo,"error_slo");check(error_slo<1,"error_slo")
    sorted_samples=sorted(samples);p99=sorted_samples[math.ceil(.99*len(samples))-1]
    return {"p99_ms":p99,"error_rate":errors/requests,"pass":p99<=latency_slo_ms and errors/requests<=error_slo}
def gate(cpu_ok,iops_ok,pool_ok,load_ok,budget_ok,approved):
    check(all(type(x) is bool for x in (cpu_ok,iops_ok,pool_ok,load_ok,budget_ok,approved)),"flags")
    names=("cpu","iops","connections","slo","budget","approval")
    blockers=[name for name,ok in zip(names,(cpu_ok,iops_ok,pool_ok,load_ok,budget_ok,approved)) if not ok]
    return {"decision":"advisory-ready" if not blockers else "hold","blockers":blockers,"production_changes":0}
def demo(overload=False):
    pods=replicas(500 if overload else 120,40,2,8)
    io=iops(3000 if overload else 600,2,5000)
    connections=pool(pods["desired"],12,160,20)
    lt=loadtest([20,35,60,90],2 if overload else 0,1000,100)
    r={"mode":"offline","forecast":forecast(100,0.01,30),"cpu_cores":cpu_cores(120,4),"pods":pods,"storage":storage(20,30,1),"iops":io,"connections":connections,"cost":cost([{"team":"data-platform","units":4,"hours":730,"usd_per_unit_hour":.18}]),"loadtest":lt,"gate":gate(not pods["saturated"],io["safe"],connections["safe"],lt["pass"],True,True),"network_calls":0,"production_changes":0}
    r["fingerprint"]=hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest()
    return r
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument("--dry-run",action="store_true");p.add_argument("--overload",action="store_true")
    a=p.parse_args(argv);print(json.dumps(demo(a.overload),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
