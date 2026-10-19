# Chapter 098 — Enterprise Observability Production Failure Injection, Chaos Engineering and Disaster Recovery Validation

**Part 20 — Final Production Observability Capstones (3/5)**

## Mission and safety contract

Validate the resilience of the Chapter 097 observability platform with **controlled, isolated staging experiments**, a measurable recovery scorecard, and independently reviewed evidence. The title describes production-oriented failure modes; **do not execute chaos experiments against production** without a separate approved change, scoped blast radius, and mature operational safeguards.

The exercise covers OpenTelemetry Collector, Prometheus, Alertmanager, Grafana, Loki, Tempo, Kubernetes, object storage, identity, backups and independent incident communications.

## Learning outcomes

1. Design hypotheses, steady-state metrics, blast-radius constraints and abort conditions before injecting faults.
2. Detect and quantify missing metrics, logs, traces, alerts and security audit records.
3. Reproduce and recover from collector restarts, cardinality spikes, backend loss and control-plane faults.
4. Verify tenant isolation and redaction after recovery, not only service health.
5. Measure real RPO/RTO against approved recovery tiers.
6. Produce a defensible GO/NO-GO decision and incident evidence package.

## Resilience architecture

```text
synthetic workload --> OTel gateway A/B --> metrics / logs / traces
                           |                    |
                      queue + retry        Prometheus / Loki / Tempo
                           |                    |
                telemetry health metrics   Grafana / Alertmanager
                           |                    |
                     out-of-band probe ---- independent test pager
                           |
            chaos controller (staging only, deny-by-default)
                           |
            immutable evidence + isolated backup / DR
```

**Principles:** prefer non-destructive faults, limit to a dedicated namespace, pin all versions, capture baseline and recovery timestamps, require abort switches and independent paging. A running pod is not proof of telemetry correctness. Replication is not a backup, and restored queries do not prove security isolation.

## Preconditions and controls

- Signed staging change record, designated incident commander, security reviewer and service owners.
- Verified Kubernetes context, target namespace, service accounts, resource quotas and network policy.
- Baseline synthetic metric, log and trace fixtures with stable IDs and timestamps.
- Tested out-of-band communication and rollback procedure.
- Snapshot/backup manifest with checksum, encryption/key access and isolated restore target.
- Defined RPO, RTO, maximum permitted dropped-signal rate, alert latency and test duration.
- No patient/customer data, real credentials, production paging receivers or destructive data mutations.
- Automatic abort for unintended namespace impact, security leakage, uncontrolled load, missing safety observer or expired change window.

## Chaos experiment catalogue

| ID | Fault hypothesis | Safe staging injection | Recovery evidence |
|---|---|---|---|
| CH-01 | Collector restart should not permanently stop ingest | restart disposable Collector Deployment | new synthetic signal query, drop counters, timeline |
| CH-02 | Gateway backpressure should be observable | bound synthetic load below staging quota | queue depth, exporter failures, loss window |
| CH-03 | Cardinality spike should be contained | limited synthetic labels and duration | active series, memory, admission/quota response |
| CH-04 | Prometheus outage should trigger independent detection | scale only disposable target or test instance | black-box probe, alert, query recovery |
| CH-05 | Loki failure should not mask metric alerts | simulate endpoint unavailable in isolated route | log gap, retry and metric alert evidence |
| CH-06 | Tempo loss should surface trace gaps | disable disposable trace exporter | trace query before/after, dropped spans |
| CH-07 | Alertmanager route fault should activate backup path | use staging-only receiver misroute | independent pager, corrected route, delivery proof |
| CH-08 | Grafana failure should not eliminate backend access | restart disposable dashboard instance | direct API queries and restored dashboards |
| CH-09 | Storage outage should respect durability policy | mock or isolate object-store endpoint | restored query, integrity and backlog evidence |
| CH-10 | Identity failure should deny unauthorized access | expired synthetic token | denied API request and audit log |
| CH-11 | Region failure should meet RPO/RTO | tabletop or isolated region simulation | clean restore, measured RPO/RTO, rollback |
| CH-12 | Recovery must preserve security boundaries | tenant A/B negative test after restore | no cross-tenant data or secret canary leakage |

Avoid network disruption of shared services and avoid cluster-wide chaos controllers unless separately reviewed.

## Sample staging-only experiment: controlled Collector restart

Run only after validating the context and the disposable namespace:

```bash
kubectl config current-context
kubectl -n obs-capstone-staging get deploy
kubectl -n obs-capstone-staging get pods
# Replace the deployment name only after confirming it is disposable.
kubectl -n obs-capstone-staging rollout restart deployment/otel-collector
kubectl -n obs-capstone-staging rollout status deployment/otel-collector --timeout=180s
```

The Deployment name is illustrative. If the resource does not exist, stop and inspect the actual staging deployment rather than running commands against another namespace. Measure the synthetic request's trace/log/metric arrival after restart and record any unrecoverable data gap.

## Metrics and recovery measurements

Define and record:

- **Detection latency:** time from fault start to independently observed incident.
- **Alert delivery latency:** time from signal threshold to receipt at test receiver.
- **Telemetry loss:** expected synthetic events minus verified stored events; account for duplicates and sampling.
- **RPO:** time between last recoverable data point and the disruption's effective point.
- **RTO:** elapsed time from incident declaration to verified restoration of required service functions.
- **Security regression:** any unauthorized tenant read, leaked canary, failed audit chain or overprivileged recovery identity.
- **Rollback time:** duration to restore known-good pinned configuration and verify signals.

Do not infer exact RPO/RTO from a synthetic manifest. A live staging drill must provide UTC timestamps, queries, storage metadata and reviewer confirmation.

## Offline executable resilience evidence gate

The following validator intentionally accepts only **lab/staging self-reported evidence**. It is useful for testing policy logic but does not verify real chaos execution.

Save `chaos_gate.py`:

```python
"""Offline staging chaos/DR acceptance gate; no infrastructure calls."""
import json
import sys
from pathlib import Path

SCENARIOS = tuple(f"CH-{n:02d}" for n in range(1, 13))
CRITICAL = frozenset(("CH-07", "CH-10", "CH-11", "CH-12"))

def valid_number(value):
    return type(value) in (int, float) and 0 <= value < float("inf")

def assess(doc):
    if not isinstance(doc, dict):
        return {"decision": "NO-GO", "passed": 0, "findings": ["manifest must be an object"]}
    findings = []
    for field in ("exercise_id", "owner", "reviewer", "change_id", "evidence_ref"):
        if not isinstance(doc.get(field), str) or not doc[field].strip():
            findings.append("missing " + field)
    if doc.get("owner") == doc.get("reviewer"):
        findings.append("independent reviewer required")
    if doc.get("environment") not in ("lab", "staging"):
        findings.append("unsafe environment")
    if doc.get("approved") is not True:
        findings.append("approval missing")
    if doc.get("destructive") is not False:
        findings.append("destructive action prohibited")
    for metric in ("rpo", "rto", "alert_latency"):
        actual = doc.get("measured_" + metric + "_minutes")
        target = doc.get("target_" + metric + "_minutes")
        if not (valid_number(actual) and valid_number(target)
                and target > 0 and actual <= target):
            findings.append(metric.upper() + " invalid or target exceeded")
    if doc.get("abort_triggered") is not False:
        findings.append("abort condition triggered or unverified")
    results = doc.get("scenarios")
    if not isinstance(results, dict):
        results = {}
        findings.append("scenario map missing")
    passed = 0
    for name in SCENARIOS:
        entry = results.get(name)
        if (isinstance(entry, dict) and entry.get("passed") is True
                and isinstance(entry.get("evidence"), str)
                and entry["evidence"].strip()):
            passed += 1
        else:
            findings.append("failed or unsupported " + name)
            if name in CRITICAL:
                findings.append("critical blocker: " + name)
    return {"decision": "GO" if not findings else "NO-GO",
            "passed": passed, "total": len(SCENARIOS), "findings": findings}

if __name__ == "__main__":
    try:
        record = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        result = assess(record)
    except (IndexError, OSError, ValueError) as exc:
        sys.exit(str(exc))
    print(json.dumps(result, indent=2))
    sys.exit(result["decision"] != "GO")
```

Save `make_fixture.py`:

```python
import json
from pathlib import Path
from chaos_gate import SCENARIOS
record = {
    "exercise_id": "OBS-098-SYNTHETIC",
    "owner": "sre", "reviewer": "security",
    "change_id": "CHG-098-TRAINING",
    "evidence_ref": "synthetic://exercise",
    "environment": "staging",
    "approved": True,
    "destructive": False,
    "abort_triggered": False,
    "target_rpo_minutes": 15,
    "measured_rpo_minutes": 5,
    "target_rto_minutes": 60,
    "measured_rto_minutes": 42,
    "target_alert_latency_minutes": 2,
    "measured_alert_latency_minutes": 1,
    "scenarios": {
        name: {"passed": True, "evidence": "synthetic://" + name}
        for name in SCENARIOS
    },
}
Path("synthetic-chaos.json").write_text(json.dumps(record, indent=2))
```

Save `test_chaos_gate.py`:

```python
import unittest
from chaos_gate import assess, SCENARIOS, CRITICAL

def good():
    return {
        "exercise_id": "test", "owner": "sre", "reviewer": "security",
        "change_id": "CHG-098", "evidence_ref": "synthetic://test",
        "environment": "staging", "approved": True,
        "destructive": False, "abort_triggered": False,
        "target_rpo_minutes": 15, "measured_rpo_minutes": 5,
        "target_rto_minutes": 60, "measured_rto_minutes": 42,
        "target_alert_latency_minutes": 2, "measured_alert_latency_minutes": 1,
        "scenarios": {name: {"passed": True, "evidence": "synthetic://" + name}
                      for name in SCENARIOS},
    }

class ChaosGateTests(unittest.TestCase):
    def test_healthy_synthetic(self):
        self.assertEqual(assess(good())["decision"], "GO")
    def test_count(self):
        self.assertEqual(len(SCENARIOS), 12)
    def test_non_object(self):
        self.assertEqual(assess([])["decision"], "NO-GO")
    def test_production_denied(self):
        self.assertEqual(assess(dict(good(), environment="production"))["decision"], "NO-GO")
    def test_unapproved_denied(self):
        self.assertEqual(assess(dict(good(), approved=False))["decision"], "NO-GO")
    def test_destructive_denied(self):
        self.assertEqual(assess(dict(good(), destructive=True))["decision"], "NO-GO")
    def test_reviewer_independence(self):
        self.assertEqual(assess(dict(good(), reviewer="sre"))["decision"], "NO-GO")
    def test_abort_triggered(self):
        self.assertEqual(assess(dict(good(), abort_triggered=True))["decision"], "NO-GO")
    def test_rpo_breach(self):
        self.assertEqual(assess(dict(good(), measured_rpo_minutes=16))["decision"], "NO-GO")
    def test_rto_breach(self):
        self.assertEqual(assess(dict(good(), measured_rto_minutes=61))["decision"], "NO-GO")
    def test_alert_latency_breach(self):
        self.assertEqual(assess(dict(good(), measured_alert_latency_minutes=3))["decision"], "NO-GO")
    def test_invalid_measurement(self):
        self.assertEqual(assess(dict(good(), measured_rto_minutes="fast"))["decision"], "NO-GO")
    def test_each_failed_scenario(self):
        for name in SCENARIOS:
            with self.subTest(name=name):
                record = good()
                record["scenarios"][name]["passed"] = False
                self.assertEqual(assess(record)["decision"], "NO-GO")
    def test_each_missing_evidence(self):
        for name in SCENARIOS:
            with self.subTest(name=name):
                record = good()
                record["scenarios"][name]["evidence"] = ""
                self.assertEqual(assess(record)["decision"], "NO-GO")
    def test_critical_scenario_blockers(self):
        for name in CRITICAL:
            with self.subTest(name=name):
                record = good()
                del record["scenarios"][name]
                self.assertTrue(any("critical blocker" in finding
                                    for finding in assess(record)["findings"]))

if __name__ == "__main__":
    unittest.main()
```

Execute:

```bash
python3 make_fixture.py
python3 chaos_gate.py synthetic-chaos.json
python3 -m unittest -v test_chaos_gate.py
```

A synthetic GO verifies only the evaluator's self-reported fixture. It is **not** evidence that a disaster recovery exercise was run or that RPO/RTO were achieved.

## Chaos execution phases

1. **Plan:** choose hypothesis, owner, affected service, scope, duration, detection signals, abort criteria and rollback.
2. **Baseline:** query synthetic metric/log/trace, check test paging and confirm clean backup.
3. **Inject:** one controlled fault at a time within the approved namespace.
4. **Observe:** collect UTC events, metrics, query outputs, exporter errors and independent detection.
5. **Abort or recover:** stop immediately on safety trigger; restore known-good pinned config.
6. **Validate:** query all three telemetry signals, paging, tenant isolation, audit and backup integrity.
7. **Measure:** calculate actual loss, RPO/RTO, alert latency and recovery gap.
8. **Review:** require independent reviewer and record corrective actions before any new experiment.

## Troubleshooting and incident scenarios

| Symptom | Likely evidence | Immediate safe action |
|---|---|---|
| Collector queue saturation | exporter failures, queue utilization | stop load, inspect backend and quotas |
| High-cardinality memory pressure | active series, OOM/restarts | stop synthetic label generator, restore limits |
| Metrics query unavailable | Prometheus readiness and TSDB logs | fail over to approved replica, preserve state |
| Missing logs/traces | backend ingest errors, object-store responses | restore route/storage and document gap |
| No alert delivery | receiver logs, silences, route config | activate out-of-band paging |
| Recovery exposes tenant data | direct API negative tests | block cutover, security escalation |
| DR restore fails | checksums, KMS, manifests | use clean immutable backup and isolated restore |
| Rollback changes schema incompatibly | CRD and storage version mismatch | stop, use compatible release and reviewed plan |

## Operational runbooks

### RB-098-01 — Stop a chaos experiment
Declare abort, halt synthetic fault generator, verify workload and namespace scope, preserve evidence, notify incident commander, roll back to approved state and do not resume without review.

### RB-098-02 — Restore Collector ingest
Check receiver traffic, processor drops, exporter retries and backend health; restore gateway, validate synthetic end-to-end signals and record irrecoverable loss.

### RB-098-03 — Recover alert delivery
Use independent paging, inspect Alertmanager clustering/routes/silences, restore test receiver and confirm delivery before normal routing.

### RB-098-04 — Clean-room storage restore
Validate versioned backup checksum, identity/KMS, object-store schema and isolation. Restore in staging, query synthetic data, recheck tenant permissions and retention.

### RB-098-05 — Regional DR activation
Declare incident and change authority, establish alternate-region dependencies, select clean recovery point, verify metrics/logs/traces/alerts and measure RPO/RTO. Do not cut over without sign-off.

### RB-098-06 — Post-incident reliability review
Create timeline, contributing factors, customer impact, data loss, control failures, SLO effect, action owners and retest schedule.

## 100-point final scorecard

| Domain | Points |
|---|---:|
| Safety, approval and blast radius | 15 |
| Fault coverage and hypotheses | 15 |
| Independent detection and alerting | 15 |
| Measured RPO/RTO and recovery | 20 |
| Telemetry correctness and data loss | 15 |
| Security, privacy and tenant isolation | 10 |
| Evidence, rollback and independent review | 10 |

All critical safety, security and DR controls are mandatory. A score of 90+ with zero critical blockers is a curriculum assessment target, not production certification. Evidence must be signed and reviewed independently.

**Next:** Chapter 099 — Enterprise Observability Operational Readiness, Incident Command and Production Reliability Acceptance.
