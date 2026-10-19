"""Offline multi-region failover, fencing and DR acceptance model. Stdlib only."""
import argparse,hashlib,json,math
class FailoverError(ValueError):pass
def require(ok,msg):
    if not ok:raise FailoverError(msg)
def region(name,healthy,lag_seconds,backup_age_minutes,restore_minutes):
    require(type(name) is str and name in ("us-east-1","us-west-2","eu-west-1"),"region")
    require(type(healthy) is bool,"health")
    require(all(type(x) in (int,float) and not isinstance(x,bool) and math.isfinite(x) and x>=0 for x in (lag_seconds,backup_age_minutes,restore_minutes)),"metrics")
    return {"name":name,"healthy":healthy,"lag_seconds":lag_seconds,"backup_age_minutes":backup_age_minutes,"restore_minutes":restore_minutes}
def lease(holder,epoch,expires_at,now):
    require(type(holder) is str and bool(holder),"holder")
    require(type(epoch) is int and epoch>=1 and type(expires_at) is int and type(now) is int and expires_at>now,"lease")
    return {"holder":holder,"epoch":epoch,"expires_at":expires_at}
def write_allowed(lease_record,holder,epoch,now):
    require(type(lease_record) is dict and set(lease_record)=={"holder","epoch","expires_at"},"lease_schema")
    require(type(holder) is str and type(epoch) is int and type(now) is int,"writer")
    return lease_record["holder"]==holder and lease_record["epoch"]==epoch and now<lease_record["expires_at"]
def elect(candidates,votes,quorum):
    require(type(candidates) is list and bool(candidates) and len(set(candidates))==len(candidates) and all(type(x) is str and bool(x) for x in candidates),"candidates")
    require(type(votes) is dict and set(votes)==set(candidates) and all(type(v) is int and v>=0 for v in votes.values()),"votes")
    require(type(quorum) is int and quorum>=1,"quorum")
    eligible=sorted(((-count,name) for name,count in votes.items() if count>=quorum))
    return None if not eligible else eligible[0][1]
def recovery(source,target,rpo_seconds,rto_minutes,fenced,quorum_ok,approval,verified):
    require(type(source) is dict and type(target) is dict and set(source)=={"name","healthy","lag_seconds","backup_age_minutes","restore_minutes"} and set(target)==set(source),"regions")
    require(type(rpo_seconds) in (int,float) and not isinstance(rpo_seconds,bool) and math.isfinite(rpo_seconds) and rpo_seconds>=0,"rpo")
    require(type(rto_minutes) in (int,float) and not isinstance(rto_minutes,bool) and math.isfinite(rto_minutes) and rto_minutes>=0,"rto")
    require(all(type(x) is bool for x in (fenced,quorum_ok,approval,verified)),"flags")
    blockers=[]
    if source["name"]==target["name"]:blockers.append("same_region")
    if not target["healthy"]:blockers.append("target_unhealthy")
    if target["lag_seconds"]>rpo_seconds:blockers.append("rpo_exceeded")
    if target["restore_minutes"]>rto_minutes:blockers.append("rto_exceeded")
    if not fenced:blockers.append("old_writer_not_fenced")
    if not quorum_ok:blockers.append("quorum_missing")
    if not approval:blockers.append("approval_missing")
    if not verified:blockers.append("data_not_verified")
    return {"decision":"advisory-ready" if not blockers else "hold","blockers":blockers,"actual_failovers":0}
def dependencies(edges):
    require(type(edges) is dict and bool(edges) and all(type(k) is str and type(v) is list and all(type(x) is str for x in v) for k,v in edges.items()),"dag")
    require(all(d in edges for ds in edges.values() for d in ds),"missing_dependency")
    seen=set();active=set();order=[]
    def visit(node):
        require(node not in active,"cycle")
        if node in seen:return
        active.add(node)
        for d in sorted(edges[node]):visit(d)
        active.remove(node);seen.add(node);order.append(node)
    for n in sorted(edges):visit(n)
    return order
def reconcile(expected,actual):
    require(type(expected) is dict and type(actual) is dict,"datasets")
    return {"missing":sorted(set(expected)-set(actual)),"extra":sorted(set(actual)-set(expected)),"mismatched":sorted(k for k in expected.keys()&actual.keys() if expected[k]!=actual[k])}
def chaos(faults):
    require(type(faults) is list and all(f in ("region_outage","partition","stale_replica","lease_expired","storage_unavailable","telemetry_gap") for f in faults),"faults")
    return {"injected":sorted(set(faults)),"safe_mode":"simulation","production_actions":0}
def demo(failure=False):
    primary=region("us-east-1",not failure,0,5,10)
    standby=region("us-west-2",True,80 if failure else 10,20,35)
    rec=recovery(primary,standby,60,60,not failure,True,True,True)
    x={"mode":"offline","regions":[primary,standby],"lease":lease("us-east-1",4,200,100),"stale_writer_allowed":write_allowed(lease("us-west-2",5,200,100),"us-east-1",4,120),"elected":elect(["us-east-1","us-west-2"],{"us-east-1":1,"us-west-2":2},2),"order":dependencies({"identity":[],"network":["identity"],"postgres":["network"],"kafka":["postgres"],"api":["kafka"]}),"recovery":rec,"reconciliation":reconcile({"a":1,"b":2},{"a":1,"b":3}),"chaos":chaos(["region_outage","partition"]),"network_calls":0,"production_changes":0}
    x["fingerprint"]=hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()
    return x
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument("--dry-run",action="store_true");p.add_argument("--failure",action="store_true")
    a=p.parse_args(argv);print(json.dumps(demo(a.failure),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
