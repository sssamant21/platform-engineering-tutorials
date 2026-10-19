"""Chapter 114: deterministic offline CDC, orchestration and reconciliation lab.
No database, Kafka, Snowflake, Elasticsearch, network, or production writes.
"""
from __future__ import annotations
from dataclasses import dataclass,field
import argparse,hashlib,json,re
class PipelineError(ValueError):pass
def check(ok,msg):
    if not ok:raise PipelineError(msg)
def event(source,entity,seq,operation,value):
    check(source in ("postgres","mongodb"),"source")
    check(type(entity) is str and bool(re.fullmatch(r"[a-z][a-z0-9_-]{2,39}",entity)),"entity")
    check(type(seq) is int and seq>=1,"sequence")
    check(operation in ("upsert","delete"),"operation")
    check(type(value) is dict and set(value)<= {"name","amount"},"payload")
    if "name" in value:check(type(value["name"]) is str and len(value["name"])<=80,"name")
    if "amount" in value:check(type(value["amount"]) is int and not isinstance(value["amount"],bool),"amount")
    return {"source":source,"entity":entity,"seq":seq,"operation":operation,"value":dict(value)}
def key(e):return e["source"]+":"+e["entity"]
@dataclass
class Checkpoints:
    offsets:dict=field(default_factory=dict)
    def advance(self,source,offset):
        check(source in ("postgres","mongodb"),"source")
        check(type(offset) is int and offset>=0,"offset")
        previous=self.offsets.get(source,-1)
        check(offset>=previous,"checkpoint_regression")
        self.offsets[source]=offset
        return offset
@dataclass
class Projection:
    records:dict=field(default_factory=dict)
    versions:dict=field(default_factory=dict)
    applied:set=field(default_factory=set)
    def apply(self,e):
        validate=event(e["source"],e["entity"],e["seq"],e["operation"],e["value"])
        k=key(validate);eid=(k,validate["seq"])
        if eid in self.applied:return "duplicate"
        prior=self.versions.get(k,0)
        check(validate["seq"]==prior+1,"gap_or_reorder")
        if validate["operation"]=="delete":self.records.pop(k,None)
        else:self.records[k]=dict(validate["value"])
        self.versions[k]=validate["seq"];self.applied.add(eid)
        return "applied"
    def snapshot(self):return {k:dict(v) for k,v in sorted(self.records.items())}
@dataclass
class Pipeline:
    checkpoints:Checkpoints=field(default_factory=Checkpoints)
    canonical:Projection=field(default_factory=Projection)
    search:Projection=field(default_factory=Projection)
    warehouse:Projection=field(default_factory=Projection)
    dlq:list=field(default_factory=list)
    def ingest(self,source,offset,e,fail_sink=None):
        check(fail_sink in (None,"search","warehouse"),"sink")
        check(source==e["source"],"source_mismatch")
        check(type(offset) is int and offset>=0,"offset")
        check(offset>self.checkpoints.offsets.get(source,-1),"offset_replay")
        # Model a preflight stage, then sink application, then checkpoint.
        # Not atomic across real external systems.
        canonical_result=self.canonical.apply(e)
        try:
            if fail_sink=="search":raise PipelineError("search_unavailable")
            self.search.apply(e)
            if fail_sink=="warehouse":raise PipelineError("warehouse_unavailable")
            self.warehouse.apply(e)
        except PipelineError as ex:
            self.dlq.append({"source":source,"offset":offset,"entity":e["entity"],"reason":str(ex)})
            return {"status":"retry_required","checkpointed":False}
        self.checkpoints.advance(source,offset)
        return {"status":canonical_result,"checkpointed":True}
    def repair(self,e):
        # Safe replay to projections after a previously failed sink.
        self.search.apply(e);self.warehouse.apply(e)
        return {"search":self.search.snapshot(),"warehouse":self.warehouse.snapshot()}
def diff(expected,actual):
    check(type(expected) is dict and type(actual) is dict,"snapshots")
    a=set(expected);b=set(actual)
    return {"missing":sorted(a-b),"extra":sorted(b-a),"mismatched":sorted(k for k in a&b if expected[k]!=actual[k])}
def plan_backfill(start,end,batch_size):
    check(all(type(x) is int for x in (start,end,batch_size)) and start>=0 and end>=start and batch_size>=1,"backfill")
    return [[i,min(i+batch_size-1,end)] for i in range(start,end+1,batch_size)]
def dag(tasks):
    check(type(tasks) is dict and all(type(k) is str and type(v) is list and all(type(d) is str for d in v) for k,v in tasks.items()),"dag")
    check(all(d in tasks for deps in tasks.values() for d in deps),"missing_dependency")
    visiting=set();visited=set();order=[]
    def visit(node):
        if node in visiting:raise PipelineError("cycle")
        if node in visited:return
        visiting.add(node)
        for dep in tasks[node]:visit(dep)
        visiting.remove(node);visited.add(node);order.append(node)
    for name in sorted(tasks):visit(name)
    return order
def gate(missing,mismatched,lag,lag_limit,approved):
    check(all(type(x) is int and x>=0 for x in (missing,mismatched,lag,lag_limit)) and type(approved) is bool,"gate")
    blockers=[]
    if missing:blockers.append("missing_records")
    if mismatched:blockers.append("mismatched_records")
    if lag>lag_limit:blockers.append("cdc_lag")
    if not approved:blockers.append("approval")
    return {"decision":"advisory-ready" if not blockers else "hold","blockers":blockers,"production_mutations":0}
def demo(partial=False):
    p=Pipeline();e=event("postgres","patient_001",1,"upsert",{"name":"Example","amount":7})
    outcome=p.ingest("postgres",0,e,"warehouse" if partial else None)
    report={"mode":"offline","dag":dag({"extract":[],"normalize":["extract"],"project":["normalize"],"reconcile":["project"]}),"outcome":outcome,"checkpoint":dict(p.checkpoints.offsets),"search_diff":diff(p.canonical.snapshot(),p.search.snapshot()),"warehouse_diff":diff(p.canonical.snapshot(),p.warehouse.snapshot()),"backfill":plan_backfill(0,9,4),"gate":gate(0,len(diff(p.canonical.snapshot(),p.warehouse.snapshot())["missing"]),0,10,True),"dlq":p.dlq,"network_calls":0,"production_mutations":0}
    report["fingerprint"]=hashlib.sha256(json.dumps(report,sort_keys=True).encode()).hexdigest()
    return report
def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument("--dry-run",action="store_true");parser.add_argument("--partial",action="store_true")
    args=parser.parse_args(argv);print(json.dumps(demo(args.partial),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
