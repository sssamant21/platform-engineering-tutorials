# Chapter 094 — Enterprise Observability Resilience, Backup, Disaster Recovery and Security Validation

**Part 19 — Enterprise Security, Governance and Reliability (4/5)**

## Objectives and operational contract

Engineer resilient observability systems that remain useful during infrastructure failure and can be restored after loss of a cluster, storage, identity provider, or region. Design explicit RPO/RTO, integrity, tenant isolation, encryption and recovery acceptance criteria. Never assume a successful backup equals a recoverable service.

**Scope:** Prometheus, Alertmanager, Grafana, Loki, Tempo, OpenTelemetry Collector, Kubernetes and object storage. This is a reference architecture, not a promise of built-in backup behavior for every edition or deployment mode.

## Reference architecture

```text
Kubernetes / cloud / DBRE workloads
          |                  |
   regional OTel gateways   independent emergency telemetry
          |                  |
    +-----+--------+         |
    |              |         |
 Prometheus HA   Loki / Tempo distributed
    |              |
 remote-write   versioned encrypted object storage
    |              |
 durable metrics   bucket replication + immutable backup copies
    +-------+------+
            |
   Grafana / Alertmanager / GitOps
            |
 isolated recovery environment
            |
 verified restore + scoped cutover
```

Deploy independent failure domains and avoid making the observability stack dependent on itself for incident detection. Keep an out-of-band paging path, break-glass access, DNS/runbook records and a minimal external health check. HA is not a substitute for backups, and cross-region replication may replicate corruption or malicious deletion.

## Resilience engineering

| Component | Critical state | Recovery approach | Important caveat |
|---|---|---|---|
| Prometheus | rules, scrape configuration, local TSDB | GitOps restore plus TSDB snapshots or remote-store recovery | TSDB snapshots require consistent procedures; remote-write does not by itself back up configuration |
| Alertmanager | routes, receivers, silences, notification log | GitOps config plus appropriately scoped persisted state | lost silences can cause alert storms; validate notification delivery |
| Grafana | dashboards, data sources, provisioning, database, secrets | API/provisioning exports and consistent database backup | dashboard exports alone do not restore users, permissions or secrets |
| Loki | tenant config, indexes/chunks, object-store data | restore config and consistent storage sets | object-store consistency, schema and retention must match |
| Tempo | traces, block metadata, configuration | restore backend storage and config | traces are often ephemeral; RPO must match retention and business need |
| OTel Collector | pipeline config, certificates, identities | immutable image + GitOps redeployment | queued/in-memory telemetry can be lost during failover |
| Kubernetes | manifests, Secrets, CRDs, persistent volumes | GitOps, encrypted secret recovery and verified volume restores | cluster restore requires version/API compatibility |

## RPO, RTO and recovery tiers

**RPO** is the maximum tolerable data loss measured from the last recoverable point. **RTO** is the maximum tolerable restoration duration after a declared disruption. Define these per service, not as a single global number. Sample planning targets below are illustrative only:

| Tier | Example service | Example RPO | Example RTO |
|---|---|---|---|
| Critical | alert routing and security audit forwarding | 5 min | 30 min |
| High | metrics querying and dashboards | 15 min | 60 min |
| Standard | retained traces and historical logs | 60 min | 4 hours |

Determine real targets with business owners and compliance teams. Test them against observed recovery durations and actual backup age. A recovered dashboard is not a successful recovery if data sources or alerting remain broken.

## Backup architecture and trust boundaries

1. Inventory stateful resources, dependencies, data owners and tenant boundaries.
2. Version GitOps manifests, alert rules, dashboards, receiver routing and provisioning.
3. Capture consistent state backups for Grafana's database, Prometheus TSDB and required PVCs.
4. Back up Loki/Tempo object data, indexes and metadata using supported storage mechanisms.
5. Encrypt in transit and at rest; keep keys and recovery permissions independently recoverable.
6. Use protected backup identities, access logs, object versioning and approved immutability controls.
7. Maintain a separately protected recovery copy with limited delete permissions.
8. Test restore into an isolated account/namespace and verify both correctness and access restrictions.

Backups must not expose raw tokens or credentials in Git. Encryption keys are not automatically recoverable from encrypted backups. Document dependencies on KMS, DNS, IAM, certificates, container registries and network routes.

## Disaster recovery workflow

**Prepare:** publish ownership, recovery order, dependencies, RPO/RTO, on-call escalation and change authority. Pre-stage minimal infrastructure with infrastructure as code.

**Detect and declare:** use independent probes to identify region loss, failed ingest, absent security logs and alert routing failure. Declare incident severity and freeze unapproved changes.

**Preserve:** capture UTC incident timeline, storage access logs, hashes, manifest versions and audit evidence. Avoid destroying the primary region before forensics or legal hold decisions.

**Restore:** establish clean IAM, keys and networking; restore configuration; validate storage consistency; deploy collectors and backends; restore Grafana and Alertmanager; run tenant isolation and redaction checks.

**Cut over:** require incident commander and security approval, scoped DNS/traffic change, replay/deduplication plan and rollback conditions. Do not promote a replica solely because it responds to health checks.

**Verify:** test ingestion, queries, alerts, paging, logs, traces, encryption, tenant separation, audit trails and backup age. Record measured RPO/RTO and customer-visible data gaps.

## Security validation after recovery

A recovery may reintroduce vulnerable images, stale service accounts, overly broad policies or deleted audit logs. Reconcile signed image digests, GitOps commit SHAs, policy-as-code results, identity scope, certificate expiry, key accessibility, retention settings and immutable evidence. For suspected compromise, restore from a known-clean recovery point, not necessarily the newest backup.

## Offline executable recovery evidence gate

Save `recovery_gate.py`:

```python
"""Offline synthetic disaster recovery evidence gate. No cloud API calls."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

CHECKS = (
    "backup_integrity", "config_restored", "metrics_query", "logs_query",
    "traces_query", "alert_delivery", "otel_ingest", "tenant_isolation",
    "encryption", "iam_least_privilege", "audit_preserved", "rollback_ready",
)

def validate(record):
    findings = []
    if not isinstance(record, dict):
        return ["expected JSON object"]
    for field in ("incident_id", "owner", "change_id", "evidence_ref"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            findings.append("missing " + field)
    if record.get("environment") not in ("lab", "staging"):
        findings.append("unsafe environment")
    if record.get("approved") is not True:
        findings.append("approval missing")
    if record.get("destructive") is not False:
        findings.append("destructive operation prohibited")
    checks = record.get("checks")
    if not isinstance(checks, dict):
        checks = {}
        findings.append("checks missing")
    for name in CHECKS:
        if checks.get(name) is not True:
            findings.append("unverified " + name)
    for actual, target, name in (
        ("measured_rpo_minutes", "target_rpo_minutes", "RPO"),
        ("measured_rto_minutes", "target_rto_minutes", "RTO"),
    ):
        a, t = record.get(actual), record.get(target)
        if (type(a) not in (int, float) or type(t) not in (int, float)
                or not (0 <= a <= t) or t <= 0):
            findings.append(name + " target not met or invalid")
    return findings

if __name__ == "__main__":
    try:
        payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        findings = validate(payload)
    except (IndexError, OSError, ValueError) as exc:
        sys.exit(str(exc))
    print(json.dumps({"status": "PASS" if not findings else "FAIL",
                      "findings": findings}, indent=2))
    sys.exit(bool(findings))
```

Save `healthy-recovery.json`:

```json
{
  "incident_id": "OBS-094-STAGING",
  "owner": "observability-sre",
  "change_id": "CHG-094",
  "evidence_ref": "synthetic-dr-evidence",
  "environment": "staging",
  "approved": true,
  "destructive": false,
  "target_rpo_minutes": 15,
  "measured_rpo_minutes": 7,
  "target_rto_minutes": 60,
  "measured_rto_minutes": 43,
  "checks": {
    "backup_integrity": true,
    "config_restored": true,
    "metrics_query": true,
    "logs_query": true,
    "traces_query": true,
    "alert_delivery": true,
    "otel_ingest": true,
    "tenant_isolation": true,
    "encryption": true,
    "iam_least_privilege": true,
    "audit_preserved": true,
    "rollback_ready": true
  }
}
```

Save `test_recovery_gate.py`:

```python
import copy
import json
import unittest
from pathlib import Path
from recovery_gate import validate, CHECKS

BASE = json.loads(Path(__file__).with_name("healthy-recovery.json").read_text())

class RecoveryGateTests(unittest.TestCase):
    def test_healthy(self):
        self.assertEqual(validate(BASE), [])
    def test_non_object(self):
        self.assertTrue(validate([]))
    def test_no_production(self):
        self.assertTrue(validate(dict(BASE, environment="production")))
    def test_no_unapproved(self):
        self.assertTrue(validate(dict(BASE, approved=False)))
    def test_no_destructive(self):
        self.assertTrue(validate(dict(BASE, destructive=True)))
    def test_rpo_breach(self):
        self.assertTrue(validate(dict(BASE, measured_rpo_minutes=16)))
    def test_rto_breach(self):
        self.assertTrue(validate(dict(BASE, measured_rto_minutes=61)))
    def test_invalid_measurement(self):
        self.assertTrue(validate(dict(BASE, measured_rto_minutes="fast")))
    def test_missing_owner(self):
        self.assertTrue(validate(dict(BASE, owner="")))
    def test_missing_checks(self):
        self.assertTrue(validate(dict(BASE, checks=None)))
    def test_boundary_values(self):
        self.assertEqual(validate(dict(BASE, measured_rpo_minutes=15,
                                       measured_rto_minutes=60)), [])
    def test_each_required_check(self):
        for check in CHECKS:
            with self.subTest(check=check):
                item = copy.deepcopy(BASE)
                item["checks"][check] = False
                self.assertTrue(validate(item))

if __name__ == "__main__":
    unittest.main()
```

Execute:

```bash
python3 recovery_gate.py healthy-recovery.json
python3 -m unittest -v test_recovery_gate.py
```

This gate checks self-reported **synthetic** evidence and cannot prove backups, restore success, security controls or elapsed real-world recovery time. Real acceptance must bind signed evidence to observed test results.

## Incident simulations and troubleshooting

| Failure | Diagnostic evidence | Safe recovery action |
|---|---|---|
| Prometheus TSDB corruption | WAL and startup logs, snapshot integrity | restore supported snapshot into isolated environment |
| Grafana database loss | DB backup checksum, migration version | restore consistent DB and provisioning state |
| Loki missing chunks | object store, index, compactor logs | restore compatible index/chunk set; verify queries |
| Tempo partial blocks | block metadata and backend logs | restore compatible object state; document trace gaps |
| Alertmanager state loss | silences and notification routing | reconcile routes, suppress duplicates with reviewed policy |
| OTel gateway outage | exporter queue, dropped records, ingress probes | restore collectors; document unrecoverable in-memory loss |
| Regional KMS outage | key availability, IAM denies | use approved DR key plan, never bypass encryption |
| Replicated deletion | version history, object audit | select clean immutable recovery point |
| Cross-tenant access after restore | auth gateway tests, denied queries | block cutover and correct identity policy |
| DNS failover mismatch | TTL, resolver, ingress and certificate tests | rollback DNS under change control |

## Production runbooks

### RB-094-01 — Lost metrics backend
Declare scope, preserve TSDB evidence, restore approved config and data, compare last recoverable sample timestamp, test PromQL and recording rules, validate Alertmanager notifications, record RPO/RTO.

### RB-094-02 — Log or trace store corruption
Freeze writes if necessary under incident approval, preserve metadata, restore consistent object-store state in staging, query synthetic tenant-specific fixtures, verify retention and access controls before cutover.

### RB-094-03 — Compromised observability control plane
Activate SOC, isolate recovery credentials, identify known-clean images/configuration, preserve forensics, restore in clean environment, rotate approved credentials and validate audit continuity.

### RB-094-04 — Regional outage
Switch to out-of-band paging, establish alternate-region IAM/KMS/network, restore dependencies in order, run read/write and tenant checks, require dual approval for traffic shift and preserve rollback.

## Hands-on staging game day

1. Capture baseline ingest-to-query latency, alert delivery and tenant access.
2. Create and verify a versioned backup of non-sensitive staging data.
3. Inject an isolated Grafana configuration or database loss.
4. Restore from the backup; verify dashboards, data sources and scoped permissions.
5. Simulate unavailable Loki/Tempo storage and observe query degradation.
6. Rebuild a disposable collector and verify synthetic event delivery.
7. Test a denied cross-tenant read and evidence retention after restore.
8. Measure backup age and elapsed recovery time against tier-specific targets.
9. Test an approved rollback and produce a UTC incident timeline.
10. Record reviewer decisions and open corrective actions for failed checks.

## 100-point acceptance rubric

| Domain | Points |
|---|---:|
| Recovery architecture and dependencies | 15 |
| Backup consistency and recoverability | 20 |
| Measured RPO and RTO | 15 |
| Alerting and ingestion restoration | 15 |
| Security, privacy and tenant isolation | 15 |
| Rollback and incident runbooks | 10 |
| Audit evidence and independent review | 10 |

A staging score of at least 85/100 with zero critical security or data-integrity failures is the *curriculum* acceptance threshold. It is not an external certification. Live DR execution, governance testing and independent compliance verification remain pending until separately evidenced.

**Next:** Chapter 095 — Enterprise Observability Security, Governance and Reliability Acceptance Capstone.
