"""Chapter 113 offline Kafka/outbox/CDC worker simulation (Python 3.11+ stdlib).
No brokers, sockets, databases, background tasks or production mutations.
"""
from __future__ import annotations
from dataclasses import dataclass,field
import argparse,hashlib,json,math,re
class PipelineError(ValueError):pass
def require(ok,code):
    if not ok:raise PipelineError(code)
def validate_event(e):
    require(type(e) is dict and set(e)=={"event_id","aggregate_id","version","payload"},"schema")
    for k in ("event_id","aggregate_id"):
        require(type(e[k]) is str and bool(re.fullmatch(r"[a-z][a-z0-9_-]{2,63}",e[k])),"identifier")
    require(type(e["version"]) is int and e["version"]>0,"version")
    require(type(e["payload"]) is dict and set(e["payload"])=={"action"} and e["payload"]["action"] in ("created","updated","deleted"),"payload")
    return json.loads(json.dumps(e,sort_keys=True))
def partition(key,count):
    require(type(key) is str and bool(key) and type(count) is int and 1<=count<=1024,"partition")
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8],"big")%count
@dataclass
class Outbox:
    records:dict=field(default_factory=dict)
    pending:list=field(default_factory=list)
    def commit(self,event):
        e=validate_event(event);ident=e["aggregate_id"];current=self.records.get(ident,0)
        require(e["version"]==current+1,"version_conflict")
        require(all(x["event_id"]!=e["event_id"] for x in self.pending),"duplicate_event")
        self.records[ident]=e["version"];self.pending.append(e)
        return {"committed":True,"outbox_count":len(self.pending)}
    def drain(self,limit):
        require(type(limit) is int and limit>0,"limit")
        batch=self.pending[:limit];self.pending=self.pending[limit:]
        return [dict(e) for e in batch]
@dataclass
class Broker:
    partitions:int=3
    logs:dict=field(default_factory=dict)
    def __post_init__(self):
        require(type(self.partitions) is int and 1<=self.partitions<=1024,"partitions")
        self.logs={i:[] for i in range(self.partitions)}
    def publish(self,event):
        e=validate_event(event);p=partition(e["aggregate_id"],self.partitions);offset=len(self.logs[p])
        self.logs[p].append(e);return {"partition":p,"offset":offset}
    def read(self,p,offset):
        require(type(p) is int and p in self.logs and type(offset) is int and offset>=0,"offset")
        return [dict(e) for e in self.logs[p][offset:]]
@dataclass
class Consumer:
    committed:dict=field(default_factory=dict)
    processed:set=field(default_factory=set)
    revisions:dict=field(default_factory=dict)
    dlq:list=field(default_factory=list)
    def consume(self,broker,p,limit=10,fail_ids=()):
        require(type(limit) is int and limit>0,"limit")
        require(type(fail_ids) in (tuple,list,set) and all(type(x) is str for x in fail_ids),"fail_ids")
        start=self.committed.get(p,-1)+1
        entries=broker.read(p,start)[:limit];results=[]
        for index,e in enumerate(entries,start):
            if e["event_id"] in fail_ids:
                self.dlq.append({"event_id":e["event_id"],"partition":p,"offset":index,"reason":"simulated_failure"})
                results.append("dlq")
            elif e["event_id"] in self.processed:results.append("duplicate")
            else:
                previous=self.revisions.get(e["aggregate_id"],0)
                require(e["version"]==previous+1,"out_of_order")
                self.revisions[e["aggregate_id"]]=e["version"];self.processed.add(e["event_id"]);results.append("processed")
            self.committed[p]=index
        return results
def admission(incoming,workers,queue):
    require(all(type(v) is int and v>=0 for v in (incoming,workers,queue)) and workers>0,"capacity")
    active=min(incoming,workers);queued=min(incoming-active,queue)
    return {"active":active,"queued":queued,"rejected":incoming-active-queued}
def retry_delays(attempts,base=100,cap=2000):
    require(type(attempts) is int and 0<=attempts<=10 and type(base) is int and base>0 and type(cap) is int and cap>=base,"retry")
    return [min(base*(2**n),cap) for n in range(attempts)]
def lag(broker,consumer):
    return {p:max(0,len(broker.logs[p])-(consumer.committed.get(p,-1)+1)) for p in broker.logs}
def slo(success,total,target=.99):
    require(type(success) is int and type(total) is int and 0<=success<=total,"counts")
    require(type(target) in (float,int) and math.isfinite(target) and 0<target<1,"target")
    return {"status":"unknown" if total==0 else "pass" if success/total>=target else "breached","remaining_bad_events":total*(1-target)-(total-success)}
def demo():
    e={"event_id":"evt_001","aggregate_id":"patient_001","version":1,"payload":{"action":"created"}}
    outbox=Outbox();commit=outbox.commit(e);broker=Broker(3)
    published=[broker.publish(x) for x in outbox.drain(10)]
    worker=Consumer();p=published[0]["partition"];results=worker.consume(broker,p)
    return {"mode":"offline","commit":commit,"published":published,"consumed":results,"lag":lag(broker,worker),"backpressure":admission(20,5,3),"retry_ms":retry_delays(4),"slo":slo(100,100),"network_calls":0,"production_mutations":0}
def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument("--dry-run",action="store_true")
    parser.parse_args(argv);print(json.dumps(demo(),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
