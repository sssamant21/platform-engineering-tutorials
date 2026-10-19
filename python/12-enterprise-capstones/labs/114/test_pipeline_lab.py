import json,unittest
from io import StringIO
from contextlib import redirect_stdout
from pipeline_lab import PipelineError,event,key,Checkpoints,Projection,Pipeline,diff,plan_backfill,dag,gate,demo,main
class Tests(unittest.TestCase):
    def reject(self,fn):
        with self.assertRaises(PipelineError):fn()
    def ev(self,seq=1,operation="upsert"):return event("postgres","patient_001",seq,operation,{"name":"Example"})
    def test_event(self):self.assertEqual(self.ev()["seq"],1)
    def test_source(self):self.reject(lambda:event("mysql","patient_001",1,"upsert",{}))
    def test_entity(self):self.reject(lambda:event("postgres","!",1,"upsert",{}))
    def test_seq_bool(self):self.reject(lambda:event("postgres","patient_001",True,"upsert",{}))
    def test_operation(self):self.reject(lambda:event("postgres","patient_001",1,"truncate",{}))
    def test_payload(self):self.reject(lambda:event("postgres","patient_001",1,"upsert",{"secret":"x"}))
    def test_key(self):self.assertEqual(key(self.ev()),"postgres:patient_001")
    def test_checkpoint(self):self.assertEqual(Checkpoints().advance("postgres",0),0)
    def test_checkpoint_equal(self):
        c=Checkpoints();c.advance("postgres",0);self.assertEqual(c.advance("postgres",0),0)
    def test_checkpoint_regression(self):
        c=Checkpoints();c.advance("postgres",2);self.reject(lambda:c.advance("postgres",1))
    def test_projection(self):self.assertEqual(Projection().apply(self.ev()),"applied")
    def test_projection_duplicate(self):
        p=Projection();p.apply(self.ev());self.assertEqual(p.apply(self.ev()),"duplicate")
    def test_projection_gap(self):self.reject(lambda:Projection().apply(self.ev(2)))
    def test_projection_delete(self):
        p=Projection();p.apply(self.ev());p.apply(self.ev(2,"delete"));self.assertEqual(p.snapshot(),{})
    def test_projection_copy(self):
        p=Projection();p.apply(self.ev());x=p.snapshot();x["postgres:patient_001"]["name"]="changed";self.assertEqual(p.snapshot()["postgres:patient_001"]["name"],"Example")
    def test_ingest(self):
        p=Pipeline();self.assertTrue(p.ingest("postgres",0,self.ev())["checkpointed"])
    def test_ingest_checkpoint(self):
        p=Pipeline();p.ingest("postgres",0,self.ev());self.assertEqual(p.checkpoints.offsets["postgres"],0)
    def test_ingest_source_mismatch(self):self.reject(lambda:Pipeline().ingest("mongodb",0,self.ev()))
    def test_ingest_offset_replay(self):
        p=Pipeline();p.ingest("postgres",0,self.ev());self.reject(lambda:p.ingest("postgres",0,self.ev()))
    def test_ingest_search_failure(self):
        p=Pipeline();self.assertFalse(p.ingest("postgres",0,self.ev(),"search")["checkpointed"]);self.assertEqual(p.dlq[0]["reason"],"search_unavailable")
    def test_ingest_warehouse_failure(self):
        p=Pipeline();self.assertFalse(p.ingest("postgres",0,self.ev(),"warehouse")["checkpointed"]);self.assertEqual(p.checkpoints.offsets,{})
    def test_repair(self):
        p=Pipeline();p.ingest("postgres",0,self.ev(),"warehouse");p.repair(self.ev());self.assertEqual(p.canonical.snapshot(),p.warehouse.snapshot())
    def test_replay_after_failure(self):
        p=Pipeline();p.ingest("postgres",0,self.ev(),"warehouse");self.assertTrue(p.ingest("postgres",0,self.ev())["checkpointed"])
    def test_diff_equal(self):self.assertEqual(diff({"a":1},{"a":1}),{"missing":[],"extra":[],"mismatched":[]})
    def test_diff_missing(self):self.assertEqual(diff({"a":1}, {})["missing"],["a"])
    def test_diff_extra(self):self.assertEqual(diff({},{"a":1})["extra"],["a"])
    def test_diff_mismatch(self):self.assertEqual(diff({"a":1},{"a":2})["mismatched"],["a"])
    def test_backfill(self):self.assertEqual(plan_backfill(0,9,4),[[0,3],[4,7],[8,9]])
    def test_backfill_bad(self):self.reject(lambda:plan_backfill(10,9,4))
    def test_dag(self):self.assertEqual(dag({"b":["a"],"a":[]}),["a","b"])
    def test_dag_cycle(self):self.reject(lambda:dag({"a":["b"],"b":["a"]}))
    def test_dag_missing(self):self.reject(lambda:dag({"a":["b"]}))
    def test_gate_ready(self):self.assertEqual(gate(0,0,0,10,True)["decision"],"advisory-ready")
    def test_gate_missing(self):self.assertIn("missing_records",gate(1,0,0,10,True)["blockers"])
    def test_gate_mismatch(self):self.assertIn("mismatched_records",gate(0,1,0,10,True)["blockers"])
    def test_gate_lag(self):self.assertIn("cdc_lag",gate(0,0,11,10,True)["blockers"])
    def test_gate_approval(self):self.assertIn("approval",gate(0,0,0,10,False)["blockers"])
    def test_gate_bad(self):self.reject(lambda:gate(-1,0,0,10,True))
    def test_demo(self):self.assertEqual(demo()["gate"]["decision"],"advisory-ready")
    def test_demo_partial(self):self.assertEqual(demo(True)["gate"]["decision"],"hold")
    def test_no_network(self):self.assertEqual(demo()["network_calls"],0)
    def test_no_writes(self):self.assertEqual(demo()["production_mutations"],0)
    def test_fingerprint(self):self.assertNotEqual(demo()["fingerprint"],demo(True)["fingerprint"])
    def test_cli(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(out.getvalue())["mode"],"offline")
    def test_partial_cli(self):
        out=StringIO()
        with redirect_stdout(out):main(["--partial"])
        self.assertEqual(json.loads(out.getvalue())["gate"]["decision"],"hold")
if __name__=="__main__":unittest.main()
