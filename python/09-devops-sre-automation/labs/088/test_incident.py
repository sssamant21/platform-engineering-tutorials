"""Deterministic offline tests for Chapter 088 sandbox incident engine."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from contextlib import redirect_stdout
from io import StringIO

from incident import (
    ALLOWED_ACTION, Plan, PolicyError, Signal, audit, correlate, execute, main,
    synthetic_diagnostics
)

class IncidentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.plan = Plan("INC-1001", "postgres-health", ALLOWED_ACTION, "disk-pressure")
        self.now = 1000.0
    def tearDown(self):
        self.tmp.cleanup()
    def approve(self, plan=None, **kwargs):
        plan = plan or self.plan
        return execute(plan, self.root, apply=True, approval_digest=plan.digest(),
                       approver="oncall", approval_expires=1200, now=self.now, **kwargs)
    def test_valid_digest(self):
        self.assertEqual(len(self.plan.digest()),64)
    def test_digest_deterministic(self):
        self.assertEqual(self.plan.digest(),self.plan.digest())
    def test_invalid_incident(self):
        with self.assertRaises(PolicyError):
            Plan("../x","postgres-health",ALLOWED_ACTION,"disk-pressure").validate()
    def test_invalid_service(self):
        with self.assertRaises(PolicyError):
            Plan("INC-1001","../../prod",ALLOWED_ACTION,"disk-pressure").validate()
    def test_action_allowlist(self):
        with self.assertRaises(PolicyError):
            Plan("INC-1001","postgres-health","restart-database","disk-pressure").validate()
    def test_invalid_rationale(self):
        with self.assertRaises(PolicyError):
            Plan("INC-1001","postgres-health",ALLOWED_ACTION,"delete-all").validate()
    def test_disk_correlation(self):
        self.assertEqual(correlate(synthetic_diagnostics(1000),1000),"disk-pressure")
    def test_error_rate_correlation(self):
        self.assertEqual(correlate([Signal("error_rate",7,990)],1000),"high-error-rate")
    def test_no_signal_correlation(self):
        self.assertEqual(correlate([],1000),"manual-exercise")
    def test_stale_diagnostic(self):
        with self.assertRaises(PolicyError):
            correlate([Signal("disk_percent",94,100)],1000)
    def test_future_diagnostic(self):
        with self.assertRaises(PolicyError):
            correlate([Signal("disk_percent",94,1001)],1000)
    def test_bad_diagnostic(self):
        with self.assertRaises(PolicyError):
            correlate([Signal("disk_percent",101,990)],1000)
    def test_unknown_diagnostic(self):
        with self.assertRaises(PolicyError):
            correlate([Signal("secret_token",5,990)],1000)
    def test_evidence_budget(self):
        with self.assertRaises(PolicyError):
            correlate([Signal("cpu_percent",5,990)]*21,1000)
    def test_dry_run_no_side_effect(self):
        result=execute(self.plan,self.root)
        self.assertEqual(result["status"],"dry-run")
        self.assertEqual(list(self.root.iterdir()),[])
    def test_missing_approval(self):
        with self.assertRaises(PolicyError):
            execute(self.plan,self.root,apply=True,now=self.now)
    def test_wrong_digest(self):
        with self.assertRaises(PolicyError):
            execute(self.plan,self.root,apply=True,approval_digest="bad",
                    approver="oncall",approval_expires=1200,now=self.now)
    def test_expired_approval(self):
        with self.assertRaises(PolicyError):
            execute(self.plan,self.root,apply=True,approval_digest=self.plan.digest(),
                    approver="oncall",approval_expires=999,now=self.now)
    def test_too_long_approval(self):
        with self.assertRaises(PolicyError):
            execute(self.plan,self.root,apply=True,approval_digest=self.plan.digest(),
                    approver="oncall",approval_expires=9999,now=self.now)
    def test_invalid_approver(self):
        with self.assertRaises(PolicyError):
            execute(self.plan,self.root,apply=True,approval_digest=self.plan.digest(),
                    approver="../../user",approval_expires=1200,now=self.now)
    def test_apply_marker(self):
        result=self.approve()
        self.assertEqual(result["status"],"applied")
        marker=self.root/result["marker"]
        self.assertEqual(json.loads(marker.read_text())["plan_digest"],self.plan.digest())
    def test_duplicate_idempotent(self):
        self.approve()
        self.assertEqual(self.approve()["status"],"already-applied")
    def test_conflicting_plan(self):
        self.approve()
        changed=Plan("INC-1001","postgres-health",ALLOWED_ACTION,"manual-exercise")
        with self.assertRaises(PolicyError):
            self.approve(changed)
    def test_tampered_marker(self):
        self.approve()
        (self.root/"INC-1001-postgres-health.marker").write_text("corrupt")
        with self.assertRaises(PolicyError):
            self.approve()
    def test_audit_events(self):
        self.approve()
        self.approve()
        events=[json.loads(line) for line in (self.root/"audit.jsonl").read_text().splitlines()]
        self.assertEqual([e["event"] for e in events],["applied","duplicate"])
        self.assertNotIn("secret",json.dumps(events))
    def test_audit_symlink_rejected(self):
        other=self.root/"other"
        other.write_text("")
        link=self.root/"audit.jsonl"
        try: link.symlink_to(other)
        except (OSError,NotImplementedError): self.skipTest("symlinks unsupported")
        with self.assertRaises(PolicyError): audit(self.root,{"event":"test"})
    def test_cli_dry_run(self):
        out=StringIO()
        with redirect_stdout(out):
            rc=main(["--sandbox",str(self.root)])
        self.assertEqual(rc,0)
        self.assertEqual(json.loads(out.getvalue())["status"],"dry-run")
    def test_cli_apply_rejected_without_approval(self):
        out=StringIO()
        with redirect_stdout(out):
            rc=main(["--sandbox",str(self.root),"--apply"])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(out.getvalue())["status"],"rejected")
    def test_nonexistent_root_rejected(self):
        with self.assertRaises(OSError):
            execute(self.plan,self.root/"missing",apply=True,
                    approval_digest=self.plan.digest(),approver="oncall",
                    approval_expires=1200,now=self.now)

if __name__=="__main__":
    unittest.main()
