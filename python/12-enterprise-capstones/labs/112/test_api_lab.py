import json,math,unittest
from contextlib import redirect_stdout
from io import StringIO
from api_lab import API,APIError,Pool,MemoryPostgres,MemorySearch,MemoryMongo,MemoryRedis,Telemetry,validate_id,validate_payload,validate_timeout,demo,main
class Tests(unittest.TestCase):
    def raises(self,fn,status=None):
        with self.assertRaises(APIError) as ctx:fn()
        if status is not None:self.assertEqual(ctx.exception.status,status)
    def payload(self,rev=1):return {"id":"record_001","name":"Patient summary","revision":rev}
    def create(self,api,key="request001"):return api.handle("POST","/v1/records",self.payload(),role="writer",key=key)
    def test_id_valid(self):self.assertEqual(validate_id("abc"),"abc")
    def test_id_short(self):self.raises(lambda:validate_id("ab"),422)
    def test_id_injection(self):self.raises(lambda:validate_id("a;DROP TABLE"),422)
    def test_payload(self):self.assertEqual(validate_payload(self.payload())["revision"],1)
    def test_payload_extra(self):self.raises(lambda:validate_payload(dict(self.payload(),admin=True)),422)
    def test_payload_bool_revision(self):self.raises(lambda:validate_payload(dict(self.payload(),revision=True)),422)
    def test_payload_control(self):self.raises(lambda:validate_payload(dict(self.payload(),name="bad\nname")),422)
    def test_payload_empty(self):self.raises(lambda:validate_payload(dict(self.payload(),name="")),422)
    def test_timeout_valid(self):self.assertEqual(validate_timeout(1000,100,800)["total_ms"],1000)
    def test_timeout_invalid(self):self.raises(lambda:validate_timeout(100,100,100),422)
    def test_timeout_negative(self):self.raises(lambda:validate_timeout(-1,1,1),422)
    def test_pool_limit(self):
        p=Pool(1);p.acquire();self.raises(p.acquire,503);p.release();self.assertEqual(p.active,0)
    def test_pool_underflow(self):self.raises(Pool(1).release,500)
    def test_pool_invalid(self):self.raises(lambda:Pool(0),422)
    def test_pg_insert(self):self.assertEqual(MemoryPostgres().upsert(self.payload())["id"],"record_001")
    def test_pg_missing(self):self.raises(lambda:MemoryPostgres().get("record_001"),404)
    def test_pg_revision_conflict(self):
        p=MemoryPostgres();p.upsert(self.payload());self.raises(lambda:p.upsert(self.payload(2),0),409)
    def test_pg_revision_update(self):
        p=MemoryPostgres();p.upsert(self.payload());self.assertEqual(p.upsert(self.payload(2),1)["revision"],2)
    def test_pg_pool_release(self):
        p=MemoryPostgres();self.raises(lambda:p.get("record_001"),404);self.assertEqual(p.pool.active,0)
    def test_search_projection(self):
        s=MemorySearch();s.project(self.payload());self.assertEqual(len(s.query("PATIENT")),1)
    def test_search_empty(self):self.assertEqual(MemorySearch().query("foo"),[])
    def test_search_limit(self):self.raises(lambda:MemorySearch().query("foo",101),422)
    def test_search_invalid(self):self.raises(lambda:MemorySearch().query(""),422)
    def test_mongo(self):
        m=MemoryMongo();m.put("record_001",{"tags":["active"],"note":"ok"});self.assertEqual(m.get("record_001")["tags"],["active"])
    def test_mongo_missing(self):self.raises(lambda:MemoryMongo().get("record_001"),404)
    def test_mongo_unknown_field(self):self.raises(lambda:MemoryMongo().put("record_001",{"password":"x"}),422)
    def test_mongo_note(self):self.raises(lambda:MemoryMongo().put("record_001",{"note":"x"*201}),422)
    def test_cache_hit(self):
        c=MemoryRedis();c.set("record_001",{"ok":True},10,now=1);self.assertEqual(c.get("record_001",2),{"ok":True})
    def test_cache_expiry(self):
        c=MemoryRedis();c.set("record_001",1,10,now=1);self.assertIsNone(c.get("record_001",11))
    def test_cache_ttl(self):self.raises(lambda:MemoryRedis().set("record_001",1,0),422)
    def test_cache_copy(self):
        c=MemoryRedis();c.set("record_001",{"a":[1]},10);x=c.get("record_001");x["a"].append(2);self.assertEqual(c.get("record_001"),{"a":[1]})
    def test_metrics(self):
        t=Telemetry();t.record(503,10);t.record(200,20);self.assertEqual(t.snapshot()["server_errors"],1)
    def test_metrics_empty(self):self.assertIsNone(Telemetry().snapshot()["p99_ms"])
    def test_metrics_invalid(self):self.raises(lambda:Telemetry().record(200,math.nan),500)
    def test_api_create(self):self.assertEqual(self.create(API())[0],201)
    def test_api_read(self):
        a=API();self.create(a);self.assertEqual(a.handle("GET","/v1/records/record_001")[0],200)
    def test_api_search(self):
        a=API();self.create(a);self.assertEqual(len(a.handle("GET","/v1/search",{"q":"Patient"})[1]["items"]),1)
    def test_api_forbidden(self):self.assertEqual(API().handle("POST","/v1/records",self.payload(),role="reader",key="request001")[0],403)
    def test_api_missing_key(self):self.assertEqual(API().handle("POST","/v1/records",self.payload(),role="writer")[0],422)
    def test_api_idempotency(self):
        a=API();self.create(a);self.assertEqual(self.create(a)[0],200);self.assertEqual(len(a.postgres.records),1)
    def test_api_key_conflict(self):
        a=API();self.create(a);self.assertEqual(a.handle("POST","/v1/records",dict(self.payload(),name="Changed"),role="writer",key="request001")[0],409)
    def test_api_not_found(self):self.assertEqual(API().handle("GET","/v1/records/record_001")[0],404)
    def test_api_route(self):self.assertEqual(API().handle("DELETE","/v1/records/record_001",role="writer")[0],404)
    def test_api_metrics(self):
        a=API();self.create(a);a.handle("GET","/v1/records/record_001");self.assertEqual(a.telemetry.snapshot()["requests"],2)
    def test_demo_offline(self):self.assertEqual(demo()["network_calls"],0)
    def test_demo_no_prod_writes(self):self.assertEqual(demo()["production_mutations"],0)
    def test_cli(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(out.getvalue())["created"][0],201)
if __name__=="__main__":unittest.main()
