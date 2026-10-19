"""Chapter 112: offline, standard-library API contract and data-access simulator.

No listening sockets, real database drivers, credentials or production mutations.
"""
from __future__ import annotations
from dataclasses import dataclass,field
from collections import defaultdict
import argparse,hashlib,json,math,re,time
class APIError(Exception):
    def __init__(self,status:int,code:str,message:str):
        super().__init__(message);self.status=status;self.code=code
    def body(self):return {"error":{"code":self.code,"message":str(self)}}
def require(condition,status,code,message):
    if not condition:raise APIError(status,code,message)
def validate_id(value):
    require(isinstance(value,str) and bool(re.fullmatch(r"[a-z][a-z0-9_-]{2,31}",value)),422,"INVALID_ID","id must be 3–32 safe characters")
    return value
def validate_payload(payload):
    require(type(payload) is dict,422,"INVALID_BODY","expected object")
    require(set(payload)=={"id","name","revision"},422,"INVALID_FIELDS","exactly id,name,revision required")
    ident=validate_id(payload["id"]);name=payload["name"];rev=payload["revision"]
    require(type(name) is str and 1<=len(name)<=80 and name.strip()==name and all(ord(c)>=32 for c in name),422,"INVALID_NAME","invalid name")
    require(type(rev) is int and rev>=1,422,"INVALID_REVISION","revision must be positive integer")
    return {"id":ident,"name":name,"revision":rev}
def validate_timeout(total_ms,pool_ms,query_ms):
    vals=(total_ms,pool_ms,query_ms)
    require(all(type(x) is int and x>0 for x in vals),422,"INVALID_TIMEOUT","positive integer timeout required")
    require(pool_ms+query_ms<=total_ms,422,"TIMEOUT_BUDGET","nested timeouts exceed total")
    return {"total_ms":total_ms,"pool_ms":pool_ms,"query_ms":query_ms}
@dataclass
class Pool:
    limit:int
    active:int=0
    def __post_init__(self):
        require(type(self.limit) is int and self.limit>0,422,"INVALID_POOL","pool limit must be positive")
    def acquire(self):
        require(self.active<self.limit,503,"POOL_EXHAUSTED","bounded pool exhausted")
        self.active+=1
    def release(self):
        require(self.active>0,500,"POOL_UNDERFLOW","unbalanced release")
        self.active-=1
@dataclass
class MemoryPostgres:
    records:dict=field(default_factory=dict)
    pool:Pool=field(default_factory=lambda:Pool(3))
    def upsert(self,payload,expected_revision=None):
        item=validate_payload(payload)
        self.pool.acquire()
        try:
            existing=self.records.get(item["id"])
            if existing is not None:
                require(type(expected_revision) is int and expected_revision==existing["revision"],409,"REVISION_CONFLICT","optimistic concurrency conflict")
                require(item["revision"]==existing["revision"]+1,409,"REVISION_CONFLICT","revision must increment by one")
            else:
                require(expected_revision is None,409,"REVISION_CONFLICT","new record requires no previous revision")
                require(item["revision"]==1,409,"REVISION_CONFLICT","new record starts at revision one")
            self.records[item["id"]]=dict(item)
            return dict(item)
        finally:self.pool.release()
    def get(self,ident):
        validate_id(ident);self.pool.acquire()
        try:
            require(ident in self.records,404,"NOT_FOUND","record not found")
            return dict(self.records[ident])
        finally:self.pool.release()
@dataclass
class MemorySearch:
    records:dict=field(default_factory=dict)
    def project(self,record):
        item=validate_payload(record);self.records[item["id"]]=dict(item)
    def query(self,term,limit=10):
        require(type(term) is str and 1<=len(term)<=80,422,"INVALID_QUERY","query term required")
        require(type(limit) is int and 1<=limit<=100,422,"INVALID_LIMIT","limit 1..100")
        return [dict(v) for _,v in sorted(self.records.items()) if term.lower() in v["name"].lower()][:limit]
@dataclass
class MemoryMongo:
    docs:dict=field(default_factory=dict)
    def put(self,ident,document):
        validate_id(ident);require(type(document) is dict and set(document)<= {"tags","note"},422,"INVALID_DOCUMENT","unsupported document fields")
        require(type(document.get("tags",[])) is list and all(type(t) is str and len(t)<=32 for t in document.get("tags",[])),422,"INVALID_TAGS","invalid tags")
        require(type(document.get("note","")) is str and len(document.get("note",""))<=200,422,"INVALID_NOTE","invalid note")
        self.docs[ident]=json.loads(json.dumps(document))
    def get(self,ident):
        validate_id(ident);require(ident in self.docs,404,"NOT_FOUND","document missing")
        return json.loads(json.dumps(self.docs[ident]))
@dataclass
class MemoryRedis:
    values:dict=field(default_factory=dict)
    def set(self,key,value,ttl_seconds,now=0):
        validate_id(key);require(type(ttl_seconds) is int and 1<=ttl_seconds<=86400,422,"INVALID_TTL","TTL must be bounded")
        require(type(now) in (int,float) and math.isfinite(now),422,"INVALID_TIME","invalid time")
        self.values[key]=(json.loads(json.dumps(value)),now+ttl_seconds)
    def get(self,key,now=0):
        validate_id(key);require(type(now) in (int,float) and math.isfinite(now),422,"INVALID_TIME","invalid time")
        val=self.values.get(key)
        if val is None or now>=val[1]:return None
        return json.loads(json.dumps(val[0]))
@dataclass
class Telemetry:
    requests:int=0
    errors:int=0
    latency_ms:list=field(default_factory=list)
    def record(self,status,elapsed_ms):
        require(type(status) is int and 100<=status<=599,500,"INVALID_STATUS","invalid status")
        require(type(elapsed_ms) in (int,float) and math.isfinite(elapsed_ms) and elapsed_ms>=0,500,"INVALID_LATENCY","invalid latency")
        self.requests+=1;self.errors+=int(status>=500);self.latency_ms.append(elapsed_ms)
    def snapshot(self):
        samples=sorted(self.latency_ms)
        p99=None if not samples else samples[math.floor((len(samples)-1)*.99)]
        return {"requests":self.requests,"server_errors":self.errors,"p99_ms":p99}
class API:
    def __init__(self):
        self.postgres=MemoryPostgres();self.search=MemorySearch();self.mongo=MemoryMongo();self.cache=MemoryRedis()
        self.telemetry=Telemetry();self.idempotency={}
    def handle(self,method,path,body=None,role="reader",key=None,expected_revision=None):
        start=time.perf_counter_ns();status=500
        try:
            require(role in {"reader","writer"},403,"FORBIDDEN","role not permitted")
            require(type(method) is str and type(path) is str,400,"BAD_REQUEST","invalid method/path")
            if method=="POST" and path=="/v1/records":
                require(role=="writer",403,"FORBIDDEN","writer role required")
                require(type(key) is str and bool(re.fullmatch(r"[a-zA-Z0-9_-]{8,64}",key)),422,"IDEMPOTENCY_KEY","valid key required")
                item=validate_payload(body);fingerprint=hashlib.sha256(json.dumps({"body":item,"expected":expected_revision},sort_keys=True).encode()).hexdigest()
                if key in self.idempotency:
                    prior_fp,prior=self.idempotency[key]
                    require(prior_fp==fingerprint,409,"IDEMPOTENCY_CONFLICT","key reused with different request")
                    status=200;return status,dict(prior)
                saved=self.postgres.upsert(item,expected_revision)
                # In production: transactional outbox, CDC, or reconciliation, not this inline projection.
                self.search.project(saved);self.cache.set(saved["id"],saved,60)
                self.idempotency[key]=(fingerprint,dict(saved));status=201;return status,saved
            if method=="GET" and path.startswith("/v1/records/"):
                ident=validate_id(path[len("/v1/records/"):])
                cached=self.cache.get(ident)
                result=cached if cached is not None else self.postgres.get(ident)
                status=200;return status,result
            if method=="GET" and path=="/v1/search":
                require(type(body) is dict and set(body)=={"q"},422,"INVALID_QUERY","q required")
                status=200;return status,{"items":self.search.query(body["q"])}
            raise APIError(404,"ROUTE_NOT_FOUND","route not found")
        except APIError as exc:
            status=exc.status;return status,exc.body()
        finally:
            self.telemetry.record(status,max(0,(time.perf_counter_ns()-start)/1_000_000))
def demo():
    api=API()
    created=api.handle("POST","/v1/records",{"id":"record_001","name":"Example","revision":1},role="writer",key="request001")
    read=api.handle("GET","/v1/records/record_001")
    search=api.handle("GET","/v1/search",{"q":"Example"})
    forbidden=api.handle("POST","/v1/records",{"id":"record_002","name":"Blocked","revision":1},role="reader",key="request002")
    return {"mode":"offline","created":created,"read":read,"search":search,"forbidden":forbidden,"metrics":api.telemetry.snapshot(),"network_calls":0,"production_mutations":0}
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument("--dry-run",action="store_true")
    p.parse_args(argv);print(json.dumps(demo(),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
