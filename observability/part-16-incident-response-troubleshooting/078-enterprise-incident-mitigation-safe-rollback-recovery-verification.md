# Chapter 078 — Enterprise Incident Mitigation, Safe Rollback and Recovery Verification

**Part 16 — Incident Response and Troubleshooting (3/5)**  
**Audience:** SRE, DBRE, platform operations, incident commanders.  
**Prerequisites:** Chapters 076–077, SLOs, Kubernetes, database change control.

## Outcomes

Choose safe, reversible incident mitigations; control rollback risk across stateful systems; verify user-facing recovery independently; document incident closure and operational evidence.

## Recovery architecture

```text
Customer impact + SLO burn -> incident commander
                               |
                        mitigation decision
                         /           \
                  reversible       high-risk
                    change          change
                      |                |
                 staging check     specialist approval
                       \             /
                       controlled execution
                               |
                 API + data + freshness SLIs
                               |
                  stable observation window
                               |
                   incident closure + RCA
```

## Core principles

**Mitigation is not root-cause resolution.** Prefer the smallest reversible change that reduces customer impact; freeze unrelated releases, preserve evidence and establish rollback criteria before action. A rollback can itself be dangerous when it reverses a schema, replays Kafka offsets or crosses a PostgreSQL leadership boundary. Incident commanders coordinate risk decisions; service owners execute approved changes.

| Surface | Safer response | Validation and risk |
|---|---|---|
| Kubernetes | revert an approved deployment revision or disable a flag | check probes, PDB, rollout and independent HTTP SLIs |
| PostgreSQL | reduce load or use fenced, rehearsed failover | validate replication, split-brain protection and data integrity |
| Redis | throttle abusive clients or repair cache strategy | watch hot keys, stale values and evictions |
| Kafka | reduce consumer pressure and restore idempotent processing | offsets, duplicates, age of oldest event |
| Elasticsearch/OpenSearch | reduce query size and concurrency | rejections, shard pressure, storage latency |
| Snowflake | resume validated tasks after checkpoint review | CDC deduplication and source-to-target freshness |

## Kubernetes staging rollback procedure

```bash
kubectl --context staging -n demo rollout history deployment/api
kubectl --context staging -n demo get deployment api -o wide
# Only after change approval and selecting a known-good revision:
kubectl --context staging -n demo rollout undo deployment/api --to-revision=2
kubectl --context staging -n demo rollout status deployment/api --timeout=180s
kubectl --context staging -n demo get pods -l app=api
```

Revision 2 is an example, not a universal known-good revision. Verify the target revision, schema compatibility, admission policies and rollback authorization before running any mutation.

## Recovery verification

Verify *independent* user-facing availability, latency and data freshness, not only pod readiness. Compare current good/total counters with pre-incident baseline, inspect fast/slow burn-rate alerts, verify Kafka backlog drain and Snowflake freshness, and confirm PostgreSQL transaction correctness. Define a stability window appropriate to traffic and incident severity. Do not mark recovered when telemetry is absent.

```promql
sum(rate(http_requests_total{job="api",code=~"5.."}[5m]))
/
clamp_min(sum(rate(http_requests_total{job="api"}[5m])), 1e-9)
```

The denominator must match the eligible request population. Include no-traffic and missing-metric guards. Check both error rate and user-visible latency.

## Failure-injection game day

Simulate a bounded canary regression in isolated staging, observe 5xx/latency SLO burn, document rollback choice, restore an approved revision and verify independent API recovery. Extend the scenario with Kafka backlog and Snowflake freshness lag to demonstrate why API readiness alone is insufficient.

## Offline synthetic recovery gate

### healthy.json

```json
{
  "owner": "recovery-sre",
  "incident_id": "INC-078",
  "environment": "staging",
  "approved": true,
  "rollback_rehearsed": true,
  "independent_recovery_verified": true,
  "destructive_action": false,
  "checks": {
    "impact": true,
    "commander": true,
    "approval": true,
    "rollback_plan": true,
    "baseline": true,
    "slo_burn": true,
    "change_provenance": true,
    "kubernetes": true,
    "postgres": true,
    "redis": true,
    "kafka": true,
    "search": true,
    "snowflake": true,
    "data_integrity": true,
    "observability": true,
    "recovery": true,
    "stability": true,
    "audit": true
  }
}
```

### recovery_gate.py

```python
"""Synthetic recovery approval gate: never changes live infrastructure."""
import json,sys
from pathlib import Path
CHECKS=["impact","commander","approval","rollback_plan","baseline","slo_burn","change_provenance","kubernetes","postgres","redis","kafka","search","snowflake","data_integrity","observability","recovery","stability","audit"]
def validate(p):
 if not isinstance(p,dict):return ["expected object"]
 e=[]
 for k in ("owner","incident_id"):
  if not isinstance(p.get(k),str) or not p[k].strip():e.append("missing "+k)
 if p.get("environment") not in ("lab","staging"):e.append("unsafe environment")
 for k in ("approved","rollback_rehearsed","independent_recovery_verified"):
  if p.get(k) is not True:e.append("missing "+k)
 c=p.get("checks")
 if not isinstance(c,dict):e.append("invalid checks");c={}
 for k in CHECKS:
  if c.get(k) is not True:e.append("unverified "+k)
 if p.get("destructive_action") is not False:e.append("unsafe action")
 return e
if __name__=="__main__":
 try:p=json.loads(Path(sys.argv[1]).read_text());e=validate(p)
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not e else "FAIL","findings":e},indent=2))
 sys.exit(bool(e))

```

### test_recovery_gate.py

```python
import copy,json,unittest
from pathlib import Path
from recovery_gate import validate
class RecoveryTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_negative_01(self):
  p=copy.deepcopy(self.p)
  p["checks"]["impact"]=False
  self.assertTrue(validate(p))
 def test_negative_02(self):
  p=copy.deepcopy(self.p)
  p["checks"]["commander"]=False
  self.assertTrue(validate(p))
 def test_negative_03(self):
  p=copy.deepcopy(self.p)
  p["checks"]["approval"]=False
  self.assertTrue(validate(p))
 def test_negative_04(self):
  p=copy.deepcopy(self.p)
  p["checks"]["rollback_plan"]=False
  self.assertTrue(validate(p))
 def test_negative_05(self):
  p=copy.deepcopy(self.p)
  p["checks"]["baseline"]=False
  self.assertTrue(validate(p))
 def test_negative_06(self):
  p=copy.deepcopy(self.p)
  p["checks"]["slo_burn"]=False
  self.assertTrue(validate(p))
 def test_negative_07(self):
  p=copy.deepcopy(self.p)
  p["checks"]["change_provenance"]=False
  self.assertTrue(validate(p))
 def test_negative_08(self):
  p=copy.deepcopy(self.p)
  p["checks"]["kubernetes"]=False
  self.assertTrue(validate(p))
 def test_negative_09(self):
  p=copy.deepcopy(self.p)
  p["checks"]["postgres"]=False
  self.assertTrue(validate(p))
 def test_negative_10(self):
  p=copy.deepcopy(self.p)
  p["checks"]["redis"]=False
  self.assertTrue(validate(p))
 def test_negative_11(self):
  p=copy.deepcopy(self.p)
  p["checks"]["kafka"]=False
  self.assertTrue(validate(p))
 def test_negative_12(self):
  p=copy.deepcopy(self.p)
  p["checks"]["search"]=False
  self.assertTrue(validate(p))
 def test_negative_13(self):
  p=copy.deepcopy(self.p)
  p["checks"]["snowflake"]=False
  self.assertTrue(validate(p))
 def test_negative_14(self):
  p=copy.deepcopy(self.p)
  p["checks"]["data_integrity"]=False
  self.assertTrue(validate(p))
 def test_negative_15(self):
  p=copy.deepcopy(self.p)
  p["checks"]["observability"]=False
  self.assertTrue(validate(p))
 def test_negative_16(self):
  p=copy.deepcopy(self.p)
  p["checks"]["recovery"]=False
  self.assertTrue(validate(p))
 def test_negative_17(self):
  p=copy.deepcopy(self.p)
  p["checks"]["stability"]=False
  self.assertTrue(validate(p))
 def test_negative_18(self):
  p=copy.deepcopy(self.p)
  p["checks"]["audit"]=False
  self.assertTrue(validate(p))
 def test_negative_19(self):
  p=copy.deepcopy(self.p)
  p["owner"]=""
  self.assertTrue(validate(p))
 def test_negative_20(self):
  p=copy.deepcopy(self.p)
  p["incident_id"]=""
  self.assertTrue(validate(p))
 def test_negative_21(self):
  p=copy.deepcopy(self.p)
  p["environment"]="production"
  self.assertTrue(validate(p))
 def test_negative_22(self):
  p=copy.deepcopy(self.p)
  p["approved"]=false
  self.assertTrue(validate(p))
 def test_negative_23(self):
  p=copy.deepcopy(self.p)
  p["rollback_rehearsed"]=false
  self.assertTrue(validate(p))
 def test_negative_24(self):
  p=copy.deepcopy(self.p)
  p["independent_recovery_verified"]=false
  self.assertTrue(validate(p))
 def test_negative_25(self):
  p=copy.deepcopy(self.p)
  p["destructive_action"]=true
  self.assertTrue(validate(p))
 def test_negative_26(self):
  p=copy.deepcopy(self.p)
  p["checks"]=None
  self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
python3 recovery_gate.py healthy.json
python3 -m unittest -v test_recovery_gate.py
```

Expected PASS and **28 authored tests**. Execution not yet verified. This gate checks synthetic attestations and cannot authorize a real production rollback.

## 24 hands-on exercises

1. Record verified customer impact.
2. Assign incident commander.
3. Freeze unrelated risky changes.
4. Identify reversible mitigation.
5. Define rollback triggers.
6. Capture baseline SLI.
7. Check alert routing.
8. Inspect release provenance.
9. Check deployment rollout status.
10. Review database transaction safety.
11. Review PostgreSQL failover fencing.
12. Review Redis cache invalidation.
13. Review Kafka offset safety.
14. Review search index aliases.
15. Review Snowflake task replay.
16. Inspect Kubernetes rollout history.
17. Simulate a canary failure.
18. Evaluate error-budget burn.
19. Execute approved staging rollback.
20. Validate traffic recovery.
21. Validate data correctness.
22. Validate backlog recovery.
23. Observe stability window.
24. Complete recovery sign-off.

## 24 production failure scenarios

1. **Canary elevated 5xx:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
2. **Rolling deploy stuck:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
3. **Rollback image missing:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
4. **Schema incompatible rollback:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
5. **PostgreSQL split brain:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
6. **Replica lag during failover:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
7. **Redis stale cache:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
8. **Kafka duplicate processing:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
9. **Kafka offset rewind:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
10. **Search alias misroute:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
11. **Search shard relocation pressure:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
12. **Snowflake duplicate CDC replay:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
13. **Snowflake freshness lag:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
14. **Kubernetes probe failure:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
15. **Kubernetes PDB block:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
16. **DNS propagation delay:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
17. **Feature flag rollback ineffective:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
18. **Retry storm:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
19. **Alert silenced:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
20. **Telemetry missing:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
21. **Partial region recovery:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
22. **Data corruption risk:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
23. **Unapproved emergency change:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.
24. **Premature incident closure:** document blast radius, reversible mitigation, approval, rollback and independent recovery evidence.

## Eight production runbooks

1. **Mitigation decision: verify impact, blast radius, options, risk, owner and rollback trigger.**
2. **Kubernetes rollback: inspect rollout history and deployment health; use approved revision only.**
3. **PostgreSQL recovery: validate replication and fencing before any failover or restore.**
4. **Kafka recovery: assess consumer offsets, idempotency and downstream replay impact.**
5. **Search and cache recovery: validate aliases, shards, Redis invalidation and client errors.**
6. **Data pipeline recovery: inspect Snowflake tasks, CDC checkpoints and freshness without blind replay.**
7. **Independent verification: compare good/total SLIs, latency, backlog and data correctness.**
8. **Incident closure: document stable observation, communications, change evidence and follow-ups.**

## 100-point assessment

| Domain | Points |
|---|---:|
| Mitigation and risk classification | 20 |
| Kubernetes and stateful rollback safety | 20 |
| Data integrity and freshness | 20 |
| Recovery verification and synthetic tests | 20 |
| Communications, audit and closure | 20 |
| **Total** | **100** |

Suggested pass: 85/100. Production sign-off requires witnessed staging rollback, specialist approval where appropriate and sustained SLI recovery.

**Companion:** [Chapter 078 lab](labs/078-enterprise-incident-mitigation-safe-rollback-recovery-verification-lab.md).

**Next:** Chapter 079 — Enterprise Incident Communications, Postmortems and Corrective Action Tracking.
