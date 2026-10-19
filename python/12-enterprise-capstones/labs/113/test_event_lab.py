import unittest,json,math
from contextlib import redirect_stdout
from io import StringIO
from event_lab import PipelineError,validate_event,partition,Outbox,Broker,Consumer,admission,retry_delays,lag,slo,demo,main
def event(eid="evt_001",aid="patient_001",version=1,action="created"):
    return {"event_id":eid,"aggregate_id":aid,"version":version,"payload":{"action":action}}
class Tests(unittest.TestCase):
    def reject(self,fn):
        with self.assertRaises(PipelineError):fn()
    def test_event(self):self.assertEqual(validate_event(event())["version"],1)
    def test_extra(self):self.reject(lambda:validate_event(dict(event(),secret="bad")))
    def test_invalid_id(self):self.reject(lambda:validate_event(event(eid="!")))
    def test_invalid_version(self):self.reject(lambda:validate_event(event(version=True)))
    def test_invalid_action(self):self.reject(lambda:validate_event(event(action="inject")))
    def test_partition_stable(self):self.assertEqual(partition("patient_001",5),partition("patient_001",5))
    def test_partition_range(self):self.assertIn(partition("patient_001",3),range(3))
    def test_partition_bad(self):self.reject(lambda:partition("",3))
    def test_partition_bad_count(self):self.reject(lambda:partition("key",0))
    def test_outbox_commit(self):self.assertTrue(Outbox().commit(event())["committed"])
    def test_outbox_atomic_model(self):
        o=Outbox();o.commit(event());self.assertEqual(o.records["patient_001"],1);self.assertEqual(len(o.pending),1)
    def test_outbox_version(self):
        o=Outbox();o.commit(event());self.reject(lambda:o.commit(event("evt_002","patient_001",3)))
    def test_outbox_duplicate(self):
        o=Outbox();o.commit(event());self.reject(lambda:o.commit(event()))
    def test_outbox_increment(self):
        o=Outbox();o.commit(event());o.commit(event("evt_002","patient_001",2,"updated"));self.assertEqual(o.records["patient_001"],2)
    def test_drain_limit(self):
        o=Outbox();o.commit(event());o.commit(event("evt_002","patient_001",2));self.assertEqual(len(o.drain(1)),1)
    def test_drain_empty(self):self.assertEqual(Outbox().drain(1),[])
    def test_drain_bad(self):self.reject(lambda:Outbox().drain(0))
    def test_broker_publish(self):
        b=Broker();self.assertEqual(b.publish(event())["offset"],0)
    def test_broker_order(self):
        b=Broker(2);a=b.publish(event());b.publish(event("evt_002","patient_001",2));self.assertEqual(len(b.read(a["partition"],0)),2)
    def test_broker_bad_partition(self):self.reject(lambda:Broker(0))
    def test_broker_bad_offset(self):self.reject(lambda:Broker().read(0,-1))
    def test_consume(self):
        b=Broker();p=b.publish(event())["partition"];c=Consumer();self.assertEqual(c.consume(b,p),["processed"])
    def test_consume_offset(self):
        b=Broker();p=b.publish(event())["partition"];c=Consumer();c.consume(b,p);self.assertEqual(c.committed[p],0)
    def test_consume_no_replay(self):
        b=Broker();p=b.publish(event())["partition"];c=Consumer();c.consume(b,p);self.assertEqual(c.consume(b,p),[])
    def test_consume_duplicate_id(self):
        b=Broker();p=b.publish(event())["partition"];b.publish(event());c=Consumer();self.assertEqual(c.consume(b,p),["processed","duplicate"])
    def test_consume_out_of_order(self):
        b=Broker();p=b.publish(event(version=2))["partition"];self.reject(lambda:Consumer().consume(b,p))
    def test_consume_dlq(self):
        b=Broker();p=b.publish(event())["partition"];c=Consumer();self.assertEqual(c.consume(b,p,fail_ids=("evt_001",)),["dlq"]);self.assertEqual(len(c.dlq),1)
    def test_consume_bad_limit(self):self.reject(lambda:Consumer().consume(Broker(),0,0))
    def test_consume_bad_fail_ids(self):self.reject(lambda:Consumer().consume(Broker(),0,1,"x"))
    def test_lag_before(self):
        b=Broker();b.publish(event());self.assertEqual(sum(lag(b,Consumer()).values()),1)
    def test_lag_after(self):
        b=Broker();p=b.publish(event())["partition"];c=Consumer();c.consume(b,p);self.assertEqual(sum(lag(b,c).values()),0)
    def test_backpressure(self):self.assertEqual(admission(20,5,3)["rejected"],12)
    def test_backpressure_ok(self):self.assertEqual(admission(2,5,3)["rejected"],0)
    def test_backpressure_bad(self):self.reject(lambda:admission(2,0,3))
    def test_retry(self):self.assertEqual(retry_delays(4),[100,200,400,800])
    def test_retry_cap(self):self.assertEqual(retry_delays(4,100,200),[100,200,200,200])
    def test_retry_bad(self):self.reject(lambda:retry_delays(11))
    def test_slo_pass(self):self.assertEqual(slo(100,100)["status"],"pass")
    def test_slo_breach(self):self.assertEqual(slo(90,100)["status"],"breached")
    def test_slo_unknown(self):self.assertEqual(slo(0,0)["status"],"unknown")
    def test_slo_invalid(self):self.reject(lambda:slo(101,100))
    def test_slo_nan(self):self.reject(lambda:slo(1,1,math.nan))
    def test_demo(self):self.assertEqual(demo()["mode"],"offline")
    def test_no_network(self):self.assertEqual(demo()["network_calls"],0)
    def test_no_production_writes(self):self.assertEqual(demo()["production_mutations"],0)
    def test_cli(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(out.getvalue())["consumed"],["processed"])
if __name__=="__main__":unittest.main()
