# Chapter 098 — Jenkins Enterprise Failure Injection, Incident Recovery and Disaster Recovery Capstone

**Part 20 — Final Enterprise Jenkins Capstone**  
**Audience:** Jenkins SRE/DBRE, incident commanders, DevOps, Kubernetes operators, security and business continuity owners.  
**Prerequisites:** Chapters 071–085 and 091–097; Python 3; approved isolated staging environment for optional real drills.

## Mission

Demonstrate how to plan, execute, measure and review Jenkins resilience experiments while protecting production. This chapter combines controlled failure injection, SLO and error-budget analysis, incident command, backup/restore, single-writer fencing, RTO/RPO verification, security and recovery evidence.

**Safety:** The executable lab is a local synthetic incident simulator; it does not kill processes, delete data, revoke identities or modify infrastructure. Any real chaos exercise requires explicit scope, written approval, isolated staging, rollback, monitoring and stop conditions.

## 1. Recovery architecture

```text
Synthetic probes + queue/agent/SCM metrics
                    |
            detection + paging
                    |
             incident commander
                    |
     triage / containment / evidence
                    |
  controller | agents | storage | IdP | SCM
                    |
       restore / failover / rollback
                    |
    critical CI acceptance + SLO validation
                    |
         RCA / COA / game-day report
```

## 2. Failure domains

| Domain | Representative fault | Validation |
|---|---|---|
| Controller | process crash, heap/GC saturation | restart and queue recovery |
| Agent pool | Kubernetes scheduling, node loss | replacement agent and critical build |
| Storage | high latency, full disk, corrupted backup | IOPS alerts and isolated restore |
| SCM | webhook outage, authentication | source checkout and event reconciliation |
| Identity | IdP outage, expired token | break-glass and least privilege |
| Plugins/JCasC | incompatible upgrade | tested rollback |
| Artifacts | registry outage or digest mismatch | immutable verification |
| Region/AZ | infrastructure disruption | documented DR and DNS cutover |
| Security | leaked CI credential | revocation and containment |

Never run two active controllers against the same writable JENKINS_HOME. Fencing and data integrity take priority over fast failover.

## 3. Incident command and severity

Define incident commander, technical lead, communications lead, scribe and service owner. Declare severity from user impact, critical CI availability, security exposure and recovery estimates. Record UTC timeline, detection source, decision log, change freeze, stakeholder updates and exit criteria.

## 4. SLO and error-budget measurement

For time-based availability:

```text
outage minutes = recovered_at - detected_at
RTO observed = recovered_at - disaster_declared_at
RPO observed = latest committed data lost at recovery point
```

Use actual timestamp evidence and clearly distinguish detection, declaration, mitigation and complete recovery. RPO cannot be inferred solely from elapsed outage time. For 99.9% time-based availability over 30 days, total downtime allowance is 43.2 minutes.

## 5. Game-day execution gates

**Before:** approve scope, identify rollback owner, verify backup and isolated restore target, establish stop conditions, baseline SLIs, protect credentials and ensure on-call participation.

**During:** inject one scoped fault at a time, record UTC timestamps, observe queue and agent recovery, enforce blast-radius and error-budget limits.

**After:** stop injection, validate synthetic CI, artifact integrity, RBAC, critical integrations, data consistency and restoration. Record observed RTO/RPO, failed hypotheses, RCA/COA and next drill date.

## 6. Recovery runbook essentials

1. Protect storage and single-writer fencing.
2. Identify last known-good backup and matching encryption keys.
3. Confirm compatible Jenkins core/Java/plugins/JCasC versions.
4. Restore into isolated environment; do not overwrite original without approval.
5. Verify users/RBAC, credentials, jobs, agents, SCM, artifact access and plugins.
6. Run critical synthetic pipelines and compare SLO baseline.
7. Approve cutover and monitor elevated error-budget burn.
8. Capture evidence, rollback route and final incident sign-off.

## 7. Executable synthetic incident and recovery validator

Save `data/drill.json`:

```json
{
  "service": "jenkins-staging",
  "scenario": "agent-pool-outage",
  "environment": "staging",
  "approved": true,
  "isolated": true,
  "single_writer_verified": true,
  "backup_verified": true,
  "rollback_ready": true,
  "stop_conditions_defined": true,
  "declared_at": "2026-10-17T10:00:00Z",
  "recovered_at": "2026-10-17T10:18:00Z",
  "latest_recovered_data_at": "2026-10-17T09:55:00Z",
  "latest_expected_data_at": "2026-10-17T10:00:00Z",
  "rto_target_minutes": 30,
  "rpo_target_minutes": 15,
  "critical_ci_passed": true,
  "artifact_integrity_passed": true,
  "rbac_verified": true
}
```

Save `scripts/drill_check.py`:

```python
#!/usr/bin/env python3
import json
import sys
from datetime import datetime
from pathlib import Path

TRUE_KEYS = (
    "approved", "isolated", "single_writer_verified", "backup_verified",
    "rollback_ready", "stop_conditions_defined", "critical_ci_passed",
    "artifact_integrity_passed", "rbac_verified",
)

def parse_utc(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("timestamps must be UTC with Z")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

def evaluate(data):
    errors = []
    for key in ("service", "scenario"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"{key} missing")
    if data.get("environment") != "staging":
        errors.append("environment must be staging")
    for key in TRUE_KEYS:
        if data.get(key) is not True:
            errors.append(f"{key} must be true")
    for key in ("rto_target_minutes", "rpo_target_minutes"):
        if type(data.get(key)) is not int or data[key] <= 0:
            errors.append(f"{key} must be positive integer")
    try:
        declared = parse_utc(data.get("declared_at"))
        recovered = parse_utc(data.get("recovered_at"))
        last_data = parse_utc(data.get("latest_recovered_data_at"))
        expected = parse_utc(data.get("latest_expected_data_at"))
        rto = (recovered - declared).total_seconds() / 60
        rpo = (expected - last_data).total_seconds() / 60
        if rto < 0 or rpo < 0:
            errors.append("negative recovery interval")
        if rto > data["rto_target_minutes"]:
            errors.append(f"RTO breached: {rto:.1f} minutes")
        if rpo > data["rpo_target_minutes"]:
            errors.append(f"RPO breached: {rpo:.1f} minutes")
    except (ValueError, TypeError, KeyError) as exc:
        errors.append(f"invalid timestamps or targets: {exc}")
    return errors

if __name__ == "__main__":
    errors = evaluate(json.loads(Path(sys.argv[1]).read_text()))
    if errors:
        print("DRILL FAIL", *errors, sep="\n")
        sys.exit(1)
    print("DRILL PASS: synthetic evidence only")
```

```bash
python3 scripts/drill_check.py data/drill.json
```

Expected modeled RTO 18 minutes, modeled RPO 5 minutes. This is synthetic evidence, **not a real backup restoration or proven production RPO**.

## 8. Automated tests

Save `tests/test_drill.py`:

```python
import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from drill_check import evaluate

class DrillTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "data/drill.json").read_text())

    def test_good(self):
        self.assertEqual(evaluate(self.data), [])

    def test_unapproved(self):
        self.data["approved"] = False
        self.assertTrue(evaluate(self.data))

    def test_rto_breach(self):
        self.data["recovered_at"] = "2026-10-17T11:00:00Z"
        self.assertTrue(evaluate(self.data))

    def test_single_writer(self):
        self.data["single_writer_verified"] = False
        self.assertTrue(evaluate(self.data))

if __name__ == "__main__":
    unittest.main()
```

```bash
python3 -m unittest discover -s tests -v
```

## 9. Negative drill

```bash
cp data/drill.json /tmp/jenkins-drill-unsafe.json
python3 - <<'PY'
import json
p = "/tmp/jenkins-drill-unsafe.json"
with open(p) as f:
    d = json.load(f)
d["approved"] = False
d["single_writer_verified"] = False
d["recovered_at"] = "2026-10-17T11:00:00Z"
with open(p, "w") as f:
    json.dump(d, f)
PY
if python3 scripts/drill_check.py /tmp/jenkins-drill-unsafe.json; then
  echo "FAIL: unsafe drill accepted"; exit 1
else
  echo "PASS: unsafe drill denied"
fi
```

## 10. Twenty-four game-day exercises

1. Define service impact and tier.
2. Assign incident command and on-call.
3. Inventory failure domains.
4. Establish SLO/error-budget baseline.
5. Define RTO/RPO and dependencies.
6. Verify backup and encryption key custody.
7. Validate isolated restore destination.
8. Define single-writer fencing.
9. Define blast radius and stop conditions.
10. Approve staging game day.
11. Simulate controller process failure.
12. Simulate agent provisioning outage.
13. Simulate storage latency.
14. Simulate SCM/webhook outage.
15. Simulate artifact registry failure.
16. Simulate SSO/credential expiry.
17. Simulate plugin/JCasC rollback.
18. Run incident communications tabletop.
19. Calculate observed synthetic RTO/RPO.
20. Run synthetic CI acceptance.
21. Verify artifact integrity and RBAC.
22. Run Python validator and unit tests.
23. Execute unsafe negative test.
24. Publish RCA/COA and 100-point assessment.

## 11. Twenty-four failure scenarios

| # | Scenario | First action |
|---|---|---|
| 01 | Controller unresponsive | assess impact |
| 02 | JVM OOM | preserve logs |
| 03 | Plugin startup failure | compatibility |
| 04 | JCasC schema error | rollback |
| 05 | Agent Pending | scheduling |
| 06 | Node lost | reschedule |
| 07 | Queue starvation | workload isolation |
| 08 | Storage full | stop writes safely |
| 09 | High IOPS latency | storage diagnosis |
| 10 | Backup missing | recovery escalation |
| 11 | Restore corrupt | alternate backup |
| 12 | Two active writers | fence |
| 13 | RTO exceeded | command escalation |
| 14 | RPO exceeded | data-loss response |
| 15 | SCM auth failed | credentials |
| 16 | Webhook delivery stopped | replay safely |
| 17 | Registry unavailable | fallback |
| 18 | Artifact digest mismatch | quarantine |
| 19 | SSO outage | break-glass |
| 20 | Credential compromised | revoke |
| 21 | DNS cutover failed | rollback |
| 22 | Synthetic CI fails after restore | hold cutover |
| 23 | Burn alert absent | telemetry incident |
| 24 | Drill without approval | abort |

## 12. Eight production runbooks

### A. Controller outage
Confirm impact, gather controller/heap/storage evidence, mitigate, validate queue and critical CI.

### B. Agent provisioning outage
Inspect cluster scheduling, quota, images, IAM, node pool and autoscaler; isolate critical workload.

### C. Storage pressure or corruption
Protect writes, inspect latency and free space, identify last consistent backup and restore only into isolated target.

### D. Disaster recovery/failover
Fence original writer, validate restore compatibility, measure RTO/RPO and run critical acceptance before routing traffic.

### E. Identity/credential incident
Activate audited break-glass if approved, revoke compromised tokens, inspect downstream actions and restore least privilege.

### F. SCM/artifact integrity outage
Pause promotions, verify webhook replay safety, artifact digests, signing and provenance before resuming.

### G. Failed upgrade/JCasC rollout
Rollback known-good versions/config, confirm agents and plugins, preserve change evidence.

### H. Failed game day or SLO breach
Stop injection, restore baseline, declare incident if needed, publish RCA/COA and reschedule after remediation.

## 13. 100-point DR acceptance

| Domain | Points |
|---|---:|
| Scope, approval, ownership and stop conditions | 20 |
| Controller/agent/storage failure handling | 20 |
| Backup/restore, RTO/RPO and single-writer safety | 25 |
| SLOs, synthetic CI and artifact validation | 15 |
| Incident communications and security | 10 |
| Tests, evidence, RCA/COA and sign-off | 10 |
| **Total** | **100** |

Suggested pass **85/100** plus mandatory gates: approved staging scope, validated backup, fenced single writer, measured real restore RTO/RPO, working critical CI, verified artifact integrity and incident owner sign-off. Offline checks cannot satisfy real recovery gates.

## 14. Evidence template

```text
UTC / environment / owner:
Approval and blast radius:
SLO/error-budget baseline:
Backup ID and encryption key custody:
Fencing and isolated restore:
Failure injection start/stop:
Incident timeline:
Observed RTO and RPO:
Critical CI/artifact/RBAC validation:
24 exercises / 24 failures:
Score / mandatory gates / RCA / COA / reviewer:
```

**Companion:** [Chapter 098 hands-on lab](labs/098-jenkins-enterprise-failure-injection-incident-recovery-disaster-recovery-capstone-check.md).  
**Next:** Chapter 099 — Jenkins Enterprise Reliability, Security and FinOps Operational Acceptance Capstone.
