# Chapter 096 — Enterprise Observability Production Capstone Architecture and Readiness Planning

**Part 20 — Final Production Observability Capstones (1/5)**

## Mission

Design an enterprise observability platform ready for a controlled production rollout. This capstone joins the preceding 95 chapters into one reference implementation and a defensible **architecture readiness decision**. It does not claim that any live environment has been deployed or certified.

### Learning outcomes

- Translate business objectives into observability SLIs, SLOs, telemetry retention, RPO/RTO and on-call requirements.
- Design a fault-tolerant, multi-cluster, multi-region architecture for metrics, logs, traces and security audit events.
- Define trust boundaries, tenant isolation, RBAC, secrets, encryption and data governance.
- Model ingestion volume, storage, cardinality, sampling, query performance and cost.
- Create GitOps promotion, disaster recovery, rollback and evidence requirements.
- Produce a tested readiness gate and a reviewable production change plan.

## Enterprise scenario and assumptions

A fictional enterprise operates three Kubernetes clusters across two regions, plus PostgreSQL, MongoDB, Kafka and cloud services. Application, infrastructure and database teams share an observability platform, while regulated audit data must remain isolated.

**Illustrative design targets (replace through stakeholder approval):**

| Objective | Initial planning target | Evidence needed |
|---|---|---|
| Critical alert delivery | p99 under 2 minutes | synthetic end-to-end alert test |
| Metrics query availability | 99.9% monthly | independent black-box probe |
| Collector pipeline availability | 99.95% monthly | exporter and receiver telemetry |
| Critical alerting RTO | 30 minutes | timed DR rehearsal |
| Critical telemetry RPO | 5 minutes | last recoverable timestamp |
| Retention | metrics 30d; logs 14d; traces 7d | legal/security approved data classification |
| Cost control | monthly budget and anomaly threshold | tagged billing and usage evidence |

These values are *training assumptions*, not universal best practices. Actual retention and availability must reflect contractual and legal obligations.

## Reference architecture

```text
                    GLOBAL CONTROL PLANE
        GitOps + policy-as-code + secret management
               identity / PKI / audit / CI
                             |
            +----------------+----------------+
            |                                 |
         REGION A                          REGION B
   cluster-1 / cluster-2                   cluster-3
   OTel agents + gateways               OTel agents + gateways
      |        |       |                    |        |
 Prometheus   logs   traces             Prometheus  logs/traces
      |        |       |                    |        |
      +----- regional buffers / queues -----+        |
                      |                              |
             metrics long-term store                 |
             Loki object storage / Tempo backend <---+
                      |
              tenant-aware query APIs
                      |
             Grafana / SLO dashboards
                      |
         Alertmanager HA / SOC integration
                      |
            independent paging channel
                      |
    encrypted versioned cross-region backup / DR
```

**Design decisions:** keep collectors close to workloads; use regional buffering only where durability requirements justify it; isolate high-cardinality and sensitive tenants; enforce tenant identity server-side at the query gateway and storage layers; separate failure domains; protect backups against replicated deletion; maintain external monitoring for the monitoring stack.

Prometheus HA, remote write, Loki and Tempo storage architectures vary by product/version and deployment mode. Validate exact behavior against the chosen release and storage backend.

## Architecture decision records

### ADR-096-01 — Telemetry transport

Use OpenTelemetry Collector agents/gateways with approved exporters, explicit retry and queue policies, and documented data-loss behavior. Exporters may drop data when queues are exhausted; measure that explicitly.

### ADR-096-02 — Metrics architecture

Use regional Prometheus collection, recording/alerting rules and an approved long-term metrics backend if required. Control label cardinality, remote-write backpressure and tenant query cost.

### ADR-096-03 — Logs and traces

Use Loki/Tempo or approved equivalents backed by encrypted object storage. Define retention by data class, ingestion quotas, trace sampling and query limits. Never assume trace sampling preserves every forensic event.

### ADR-096-04 — Identity and tenancy

Use SSO for humans, short-lived workload identities, namespace/network controls and enforced tenant identity at each backend. Test direct API access, not only dashboards.

### ADR-096-05 — Security operations

Forward security events to an independently monitored SOC channel. Alert on auth failures, sensitive config changes, disabled collectors, telemetry drops and unexpected exporter destinations.

### ADR-096-06 — Change and recovery

Use GitOps with pinned image digests, approvals, policy checks, staging promotion, rollback and isolated restore tests. Backup success is not recovery success.

## Capacity planning

Define the following per region and tenant:

- **Metrics series:** `active_series = targets × metrics_per_target × cardinality_multiplier`.
- **Samples/day:** `active_series × (86400 / scrape_interval_seconds)`.
- **Raw sample rate:** `samples/day / 86400`.
- **Log volume/day:** `events_per_second × average_event_bytes × 86400`.
- **Trace ingest/day:** `spans_per_second × average_span_bytes × 86400`.
- **Retention storage:** `daily_ingest × retention_days × effective_storage_factor`.

These are rough planning equations. Measure compression, indexes, replication, WAL overhead, object-store requests, compaction, query cache and network egress in staging. Avoid using unvalidated compression ratios as production commitments.

### Worked example

With 100,000 active series and 30-second scrapes, expect approximately 288 million samples/day before recording rules and replication. At 5,000 log events/s averaging 800 bytes, raw logs are approximately 345.6 GB/day before compression and indexes. Use these figures to design a load test, not to choose final instance sizes.

## Deployment phases and ownership

| Phase | Deliverable | Owner | Exit gate |
|---|---|---|---|
| 0 — Discovery | inventory, data classification, critical journeys | SRE + DBRE + application owners | requirements signed |
| 1 — Design | ADRs, diagrams, SLOs, RPO/RTO, threat model | platform architect | architecture review |
| 2 — Foundation | identity, networking, keys, object storage, GitOps | platform/security | policy validation |
| 3 — Telemetry | collectors, metrics, logs, traces, dashboards | observability SRE | end-to-end synthetic tests |
| 4 — Resilience | load tests, alert routing, backup and restore | SRE + SOC | timed game day |
| 5 — Acceptance | evidence manifest, scorecard, rollback plan | independent reviewers | formal go/no-go |

## Readiness evidence contract

All fields in the gate below represent **self-reported synthetic evidence** until backed by real reviewed test artifacts. The offline script does not contact Kubernetes, GitHub, cloud APIs or monitoring systems.

Save `readiness_gate.py`:

```python
"""Fail-closed, offline architecture-readiness manifest evaluator."""
import json
import sys
from pathlib import Path

DOMAINS = {
    "requirements_signed": 10,
    "architecture_reviewed": 10,
    "slo_defined": 10,
    "capacity_tested": 10,
    "security_reviewed": 15,
    "tenant_isolation_tested": 10,
    "governance_reviewed": 10,
    "alerting_tested": 10,
    "dr_tested": 10,
    "rollback_tested": 5,
}
CRITICAL = {"security_reviewed", "tenant_isolation_tested", "alerting_tested", "dr_tested"}
assert sum(DOMAINS.values()) == 100

def assess(doc):
    if not isinstance(doc, dict):
        return {"decision": "NO-GO", "score": 0, "findings": ["manifest must be an object"]}
    findings = []
    for field in ("project", "owner", "reviewer", "change_id", "architecture_ref"):
        if not isinstance(doc.get(field), str) or not doc[field].strip():
            findings.append("missing " + field)
    if doc.get("reviewer") == doc.get("owner"):
        findings.append("independent reviewer required")
    if doc.get("environment") not in ("lab", "staging"):
        findings.append("unsafe environment")
    if doc.get("approved") is not True:
        findings.append("approval missing")
    if doc.get("destructive") is not False:
        findings.append("destructive actions prohibited")
    evidence = doc.get("evidence")
    if not isinstance(evidence, dict):
        evidence = {}
        findings.append("evidence map missing")
    score = 0
    for domain, weight in DOMAINS.items():
        entry = evidence.get(domain)
        if (isinstance(entry, dict)
            and entry.get("passed") is True
            and isinstance(entry.get("ref"), str)
            and entry["ref"].strip()):
            score += weight
        else:
            findings.append("failed or unsupported " + domain)
            if domain in CRITICAL:
                findings.append("critical blocker: " + domain)
    if score < 90:
        findings.append("score below 90")
    return {"decision": "GO" if not findings else "NO-GO",
            "score": score, "findings": findings}

if __name__ == "__main__":
    try:
        doc = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        result = assess(doc)
    except (IndexError, OSError, ValueError) as exc:
        sys.exit(str(exc))
    print(json.dumps(result, indent=2))
    sys.exit(result["decision"] != "GO")
```

Save `make_fixture.py`:

```python
import json
from pathlib import Path
from readiness_gate import DOMAINS
fixture = {
    "project": "observability-capstone-synthetic",
    "owner": "platform-sre",
    "reviewer": "independent-security-reviewer",
    "change_id": "CHG-096-TRAINING",
    "architecture_ref": "synthetic://architecture",
    "environment": "staging",
    "approved": True,
    "destructive": False,
    "evidence": {name: {"passed": True, "ref": "synthetic://" + name}
                 for name in DOMAINS},
}
Path("synthetic-readiness.json").write_text(json.dumps(fixture, indent=2))
```

Save `test_readiness_gate.py`:

```python
import copy
import unittest
from readiness_gate import DOMAINS, CRITICAL, assess

def fixture():
    return {
        "project": "test", "owner": "sre", "reviewer": "security",
        "change_id": "CHG-096", "architecture_ref": "synthetic://diagram",
        "environment": "staging", "approved": True, "destructive": False,
        "evidence": {name: {"passed": True, "ref": "synthetic://" + name}
                     for name in DOMAINS},
    }

class ReadinessTests(unittest.TestCase):
    def test_weights(self):
        self.assertEqual(sum(DOMAINS.values()), 100)
    def test_clean_synthetic_fixture(self):
        self.assertEqual(assess(fixture())["decision"], "GO")
    def test_not_object(self):
        self.assertEqual(assess([])["decision"], "NO-GO")
    def test_production_denied(self):
        self.assertEqual(assess(dict(fixture(), environment="production"))["decision"], "NO-GO")
    def test_unapproved_denied(self):
        self.assertEqual(assess(dict(fixture(), approved=False))["decision"], "NO-GO")
    def test_destructive_denied(self):
        self.assertEqual(assess(dict(fixture(), destructive=True))["decision"], "NO-GO")
    def test_independent_reviewer(self):
        self.assertEqual(assess(dict(fixture(), reviewer="sre"))["decision"], "NO-GO")
    def test_missing_architecture(self):
        self.assertEqual(assess(dict(fixture(), architecture_ref=""))["decision"], "NO-GO")
    def test_missing_evidence(self):
        self.assertEqual(assess(dict(fixture(), evidence=None))["decision"], "NO-GO")
    def test_each_failed_domain(self):
        for domain in DOMAINS:
            with self.subTest(domain=domain):
                doc = fixture()
                doc["evidence"][domain]["passed"] = False
                self.assertEqual(assess(doc)["decision"], "NO-GO")
    def test_each_missing_reference(self):
        for domain in DOMAINS:
            with self.subTest(domain=domain):
                doc = fixture()
                doc["evidence"][domain]["ref"] = ""
                self.assertEqual(assess(doc)["decision"], "NO-GO")
    def test_critical_failures(self):
        for domain in CRITICAL:
            with self.subTest(domain=domain):
                doc = fixture()
                del doc["evidence"][domain]
                self.assertTrue(any("critical blocker" in item
                                    for item in assess(doc)["findings"]))

if __name__ == "__main__":
    unittest.main()
```

Execute:

```bash
python3 make_fixture.py
python3 readiness_gate.py synthetic-readiness.json
python3 -m unittest -v test_readiness_gate.py
```

The synthetic fixture should return `GO` with 100 points, demonstrating the evaluator's happy path only. Any missing/failed domain produces NO-GO. Real acceptance requires signed, traceable staging evidence and independent review.

## Failure injection scenarios

| Scenario | Detection and evidence | Safe remediation |
|---|---|---|
| Regional collector outage | dropped spans/metrics, exporter queue, black-box probe | restore approved gateway, validate data gaps |
| Metric cardinality explosion | active series, ingestion latency, memory pressure | limit unbounded labels and apply tenant budgets |
| Loki object store unavailable | ingestion and query failures, backend errors | restore access and validate chunk/index integrity |
| Tempo sampling misconfiguration | missing synthetic trace IDs | correct sampler, document irrecoverable spans |
| Grafana SSO outage | login failures and auth logs | use approved break-glass path with audit |
| Alertmanager paging failure | synthetic alert undelivered | out-of-band paging and route rollback |
| Cross-tenant query exposure | denied-query negative tests fail | block cutover, fix backend identity boundary |
| Backup corruption | checksum mismatch and failed clean restore | restore immutable known-good copy |
| CI/CD policy bypass | unapproved image/config in staging | stop promotion and reconcile GitOps |
| Budget overrun | telemetry ingest and storage anomaly | adjust quotas/sampling after SLO review |

## Production runbooks

### RB-096-01 — Readiness review NO-GO

Stop rollout; capture failed domain and evidence; assign owner, severity, due date and reviewer; rerun affected and regression tests after remediation.

### RB-096-02 — Telemetry pipeline degradation

Compare incoming versus exported signals, queue saturation, dropped telemetry and network errors. Route to approved regional failover if tested. Preserve customer-impact timeline.

### RB-096-03 — Alerting outage

Use independent pager, verify Alertmanager cluster/receivers, validate synthetic notification, reconcile missed incidents and restore normal routing only with approval.

### RB-096-04 — Tenant isolation incident

Block affected access path, preserve audit records, involve security/privacy teams, test every direct backend endpoint and require independent sign-off.

### RB-096-05 — Disaster recovery activation

Declare severity, choose clean recovery point, restore dependencies and keys, validate end-to-end queries and alerting, measure RPO/RTO, and require change approval for traffic cutover.

## 100-point architecture acceptance rubric

The 10 domains in `readiness_gate.py` total 100 points. All domains require passing evidence, no critical blockers, and a score of at least 90. Because every domain is mandatory, a full GO currently requires 100/100; scores below that are diagnostic and do not authorize exceptions. Any governance exception requires separate written approval and revised scope.

## Required capstone artifacts

1. Context, logical and deployment architecture diagrams.
2. ADRs, dependency graph and component version matrix.
3. Data classification and retention matrix.
4. SLI/SLO and alert routing catalogue.
5. Capacity forecast, load-test plan and cost budget.
6. Security threat model and tenant isolation test plan.
7. Backup/DR architecture, measured RPO/RTO plan and rollback.
8. GitOps promotion pipeline and policy gate design.
9. Incident runbooks, ownership and escalation matrix.
10. Signed readiness scorecard with evidence and open risks.

**Status:** Chapter and lab publication is independent of live validation. Actual infrastructure testing, architecture approval and compliance sign-off remain pending until evidence exists.

**Next:** Chapter 097 — Enterprise Observability Production Deployment, Integration and End-to-End Validation.
