"""Offline automated tests for GitOps progressive release simulator."""
import json,unittest
from contextlib import redirect_stdout
from io import StringIO
from release import Release,Observed,ReleaseError,rollout,progressive,release_plan,reconcile_git,demo,main
class Tests(unittest.TestCase):
    def setUp(self):
        self.r=Release("sre-lab","patient-api","sha256:"+"a"*64,2,"git-123")
        self.o=Observed(3,3,2,2,self.r.image,self.r.revision)
        self.samples=[{"requests":100,"errors":0,"latencies_ms":[120]*100}]
        self.approval={"approved":True,"plan_digest":self.r.digest(),"rollback_tested":True,"owner_assigned":True}
    def test_valid(self):self.r.validate()
    def test_bad_namespace(self):
        with self.assertRaises(ReleaseError):Release("../prod","svc",self.r.image,2,"rev").validate()
    def test_mutable_image(self):
        with self.assertRaises(ReleaseError):Release("sre-lab","svc","nginx:latest",2,"rev").validate()
    def test_zero_replicas(self):
        with self.assertRaises(ReleaseError):Release("sre-lab","svc",self.r.image,0,"rev").validate()
    def test_bad_revision(self):
        with self.assertRaises(ReleaseError):Release("sre-lab","svc",self.r.image,2,"../bad").validate()
    def test_digest(self):self.assertEqual(self.r.digest(),self.r.digest())
    def test_healthy(self):self.assertEqual(rollout(self.r,self.o),"healthy")
    def test_generation(self):
        self.assertEqual(rollout(self.r,Observed(3,2,2,2,self.r.image,self.r.revision)),"progressing")
    def test_replicas(self):
        self.assertEqual(rollout(self.r,Observed(3,3,2,1,self.r.image,self.r.revision)),"progressing")
    def test_image_drift(self):
        self.assertEqual(rollout(self.r,Observed(3,3,2,2,"sha256:"+"b"*64,self.r.revision)),"drift")
    def test_git_drift(self):
        self.assertEqual(rollout(self.r,Observed(3,3,2,2,self.r.image,"other")),"drift")
    def test_invalid_counters(self):
        with self.assertRaises(ReleaseError):rollout(self.r,Observed(-1,0,0,0,self.r.image,self.r.revision))
    def test_no_telemetry(self):self.assertEqual(progressive([])["reason"],"no-telemetry")
    def test_low_traffic(self):
        self.assertEqual(progressive([{"requests":1,"errors":0,"latencies_ms":[1]}])["decision"],"hold")
    def test_canary_pass(self):self.assertEqual(progressive(self.samples)["decision"],"promote")
    def test_canary_errors(self):
        self.assertEqual(progressive([{"requests":100,"errors":3,"latencies_ms":[1]*100}])["decision"],"rollback-proposal")
    def test_canary_latency(self):
        self.assertEqual(progressive([{"requests":100,"errors":0,"latencies_ms":[900]*100}])["decision"],"rollback-proposal")
    def test_bad_sample(self):
        with self.assertRaises(ReleaseError):progressive([{"requests":10,"errors":11,"latencies_ms":[1]*10}])
    def test_bad_latencies(self):
        with self.assertRaises(ReleaseError):progressive([{"requests":10,"errors":0,"latencies_ms":[1]}])
    def test_bad_policy(self):
        with self.assertRaises(ReleaseError):progressive(self.samples,min_requests=0)
    def test_promote(self):
        self.assertEqual(release_plan(self.r,self.o,self.samples,approvals=self.approval)["action"],"propose-promotion")
    def test_no_approval(self):self.assertEqual(release_plan(self.r,self.o,self.samples)["action"],"hold")
    def test_wrong_digest(self):
        self.assertEqual(release_plan(self.r,self.o,self.samples,approvals=dict(self.approval,plan_digest="bad"))["action"],"hold")
    def test_rollback_missing(self):
        self.assertEqual(release_plan(self.r,self.o,self.samples,approvals=dict(self.approval,rollback_tested=False))["action"],"hold")
    def test_canary_fail(self):
        s=[{"requests":100,"errors":5,"latencies_ms":[800]*100}]
        self.assertEqual(release_plan(self.r,self.o,s,approvals=self.approval)["action"],"propose-rollback")
    def test_canary_fail_unapproved(self):
        s=[{"requests":100,"errors":5,"latencies_ms":[800]*100}]
        self.assertEqual(release_plan(self.r,self.o,s)["action"],"hold-for-approval")
    def test_no_mutations(self):
        self.assertEqual(release_plan(self.r,self.o,self.samples,approvals=self.approval)["mutations"],0)
    def test_git_synced(self):self.assertEqual(reconcile_git(self.r,self.o)["sync"],"synced")
    def test_git_drift(self):
        self.assertEqual(reconcile_git(self.r,Observed(3,3,2,2,self.r.image,"wrong"))["sync"],"out-of-sync")
    def test_demo(self):self.assertEqual(demo()["action"],"propose-promotion")
    def test_demo_fail(self):self.assertEqual(demo(True)["action"],"propose-rollback")
    def test_cli(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--dry-run"]),0)
        self.assertEqual(json.loads(out.getvalue())["network_calls"],0)
    def test_cli_fail(self):
        out=StringIO()
        with redirect_stdout(out):self.assertEqual(main(["--fail-canary"]),0)
        self.assertEqual(json.loads(out.getvalue())["action"],"propose-rollback")
if __name__=="__main__":unittest.main()
