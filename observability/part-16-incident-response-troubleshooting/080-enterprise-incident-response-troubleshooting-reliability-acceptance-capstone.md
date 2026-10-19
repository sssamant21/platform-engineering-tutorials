# Chapter 080 — Enterprise Incident Response, Troubleshooting and Reliability Acceptance Capstone

**Part 16 — Incident Response and Troubleshooting: Final Capstone (5/5)**  
**Audience:** SRE, DBRE, incident commanders, service owners, platform engineers.  
**Prerequisites:** Chapters 076–079; Prometheus, Grafana, Loki, Tempo, Kubernetes and data-platform observability.

## Mission

Demonstrate end-to-end enterprise incident readiness from customer-impact detection to incident command, SLO-based severity, signal correlation, safe mitigation, independent recovery, communications, blameless postmortem and corrective action verification.

## Reference architecture

```text
User journeys / SLOs / synthetic probes
                   |
        Prometheus / Grafana / Alertmanager
                   |
            on-call escalation
                   |
             incident commander
             /       |       \
         operations  comms   scribe
              |        |       |
          Loki + Tempo + deployment history
                   |
      PostgreSQL / Redis / Kafka / Search / Snowflake
                   |
          causal hypotheses + evidence
                   |
        approved reversible mitigation
                   |
       independent API + data recovery
                   |
        postmortem + action tracking
```

## Enterprise acceptance criteria

| Area | Acceptance evidence |
|---|---|
| Severity | SEV policy maps verified user impact, duration, scope and criticality |
| On-call | primary/secondary and specialist escalation tested in staging |
| Detection | user-facing SLIs and paired fast/slow burn alerts validated |
| Correlation | metrics, logs, traces, UTC change history and dependency evidence |
| Communications | named lead, verified updates, next UTC update, redaction |
| Mitigation | approved reversible action with explicit rollback trigger |
| Recovery | independent availability, latency, data correctness and freshness |
| Governance | blameless postmortem and owned, measurable corrective actions |

## SLO-driven incident prioritization

For a 99.9% request SLO, error budget fraction is 0.001. A fast burn of 14.4× consumes budget rapidly; paired 5m and 1h alert windows reduce transient noise. A 30m and 6h 6× pair supports sustained burn detection. Severity still depends on real customer impact and criticality. Missing telemetry must never be treated as healthy.

```promql
sum(rate(http_requests_total{job="api",code=~"5.."}[5m]))
/
clamp_min(sum(rate(http_requests_total{job="api"}[5m])), 1e-9)
```

Adapt metric names and eligible-event filters. Verify numerator and denominator populations match and implement absent-series/low-traffic handling.

## Production incident game day

A staged release causes a request retry storm, PostgreSQL pool contention, Redis latency and elevated API 5xx. Kafka backlog then increases Snowflake ingestion freshness lag. The incident commander assigns triage owners, validates customer impact, checks logs/traces and change history, tests competing hypotheses, approves a bounded rollback and monitors independent API and freshness recovery. Communications records verified updates. The review identifies trigger, contributing factors, detection gaps and measurable preventive actions.

## Safety and recovery boundaries

Kubernetes rollbacks require approved known-good revisions and schema compatibility. PostgreSQL failover needs fencing and replication checks. Kafka offset rewinds and Snowflake CDC replay can duplicate data; do not run blind replays. Elasticsearch alias changes and Redis invalidations require separate consistency verification. This capstone provides no authorization to mutate production.

## Offline synthetic acceptance gate

### healthy.json

```json
{
  "owner": "enterprise-incident-sre",
  "environment": "staging",
  "incident_id": "INC-080",
  "severity": "SEV2",
  "approved": true,
  "independent_recovery_verified": true,
  "corrective_actions_owned": true,
  "destructive_action": false,
  "checks": {
    "ownership": true,
    "severity": true,
    "oncall": true,
    "communications": true,
    "utc_timeline": true,
    "customer_impact": true,
    "availability_sli": true,
    "latency_sli": true,
    "freshness_sli": true,
    "burn_alerts": true,
    "metrics": true,
    "logs": true,
    "traces": true,
    "kubernetes": true,
    "postgres": true,
    "redis": true,
    "kafka": true,
    "search": true,
    "snowflake": true,
    "hypotheses": true,
    "approval": true,
    "rollback": true,
    "recovery": true,
    "postmortem": true
  }
}
```

### acceptance_gate.py

```python
"""Offline synthetic incident acceptance gate; never changes production."""
import json,sys
from pathlib import Path
CHECKS=["ownership","severity","oncall","communications","utc_timeline","customer_impact","availability_sli","latency_sli","freshness_sli","burn_alerts","metrics","logs","traces","kubernetes","postgres","redis","kafka","search","snowflake","hypotheses","approval","rollback","recovery","postmortem"]
def validate(p):
 if not isinstance(p,dict):return ["expected object"]
 e=[]
 for k in ("owner","incident_id"):
  if not isinstance(p.get(k),str) or not p[k].strip():e.append("missing "+k)
 if p.get("environment") not in ("lab","staging"):e.append("unsafe environment")
 if p.get("severity") not in ("SEV1","SEV2","SEV3"):e.append("invalid severity")
 for k in ("approved","independent_recovery_verified","corrective_actions_owned"):
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

### test_acceptance_gate.py

```python
import copy,json,unittest
from pathlib import Path
from acceptance_gate import validate
class AcceptanceTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_negative_01(self):
  p=copy.deepcopy(self.p)
  p["checks"]["ownership"]=False
  self.assertTrue(validate(p))
 def test_negative_02(self):
  p=copy.deepcopy(self.p)
  p["checks"]["severity"]=False
  self.assertTrue(validate(p))
 def test_negative_03(self):
  p=copy.deepcopy(self.p)
  p["checks"]["oncall"]=False
  self.assertTrue(validate(p))
 def test_negative_04(self):
  p=copy.deepcopy(self.p)
  p["checks"]["communications"]=False
  self.assertTrue(validate(p))
 def test_negative_05(self):
  p=copy.deepcopy(self.p)
  p["checks"]["utc_timeline"]=False
  self.assertTrue(validate(p))
 def test_negative_06(self):
  p=copy.deepcopy(self.p)
  p["checks"]["customer_impact"]=False
  self.assertTrue(validate(p))
 def test_negative_07(self):
  p=copy.deepcopy(self.p)
  p["checks"]["availability_sli"]=False
  self.assertTrue(validate(p))
 def test_negative_08(self):
  p=copy.deepcopy(self.p)
  p["checks"]["latency_sli"]=False
  self.assertTrue(validate(p))
 def test_negative_09(self):
  p=copy.deepcopy(self.p)
  p["checks"]["freshness_sli"]=False
  self.assertTrue(validate(p))
 def test_negative_10(self):
  p=copy.deepcopy(self.p)
  p["checks"]["burn_alerts"]=False
  self.assertTrue(validate(p))
 def test_negative_11(self):
  p=copy.deepcopy(self.p)
  p["checks"]["metrics"]=False
  self.assertTrue(validate(p))
 def test_negative_12(self):
  p=copy.deepcopy(self.p)
  p["checks"]["logs"]=False
  self.assertTrue(validate(p))
 def test_negative_13(self):
  p=copy.deepcopy(self.p)
  p["checks"]["traces"]=False
  self.assertTrue(validate(p))
 def test_negative_14(self):
  p=copy.deepcopy(self.p)
  p["checks"]["kubernetes"]=False
  self.assertTrue(validate(p))
 def test_negative_15(self):
  p=copy.deepcopy(self.p)
  p["checks"]["postgres"]=False
  self.assertTrue(validate(p))
 def test_negative_16(self):
  p=copy.deepcopy(self.p)
  p["checks"]["redis"]=False
  self.assertTrue(validate(p))
 def test_negative_17(self):
  p=copy.deepcopy(self.p)
  p["checks"]["kafka"]=False
  self.assertTrue(validate(p))
 def test_negative_18(self):
  p=copy.deepcopy(self.p)
  p["checks"]["search"]=False
  self.assertTrue(validate(p))
 def test_negative_19(self):
  p=copy.deepcopy(self.p)
  p["checks"]["snowflake"]=False
  self.assertTrue(validate(p))
 def test_negative_20(self):
  p=copy.deepcopy(self.p)
  p["checks"]["hypotheses"]=False
  self.assertTrue(validate(p))
 def test_negative_21(self):
  p=copy.deepcopy(self.p)
  p["checks"]["approval"]=False
  self.assertTrue(validate(p))
 def test_negative_22(self):
  p=copy.deepcopy(self.p)
  p["checks"]["rollback"]=False
  self.assertTrue(validate(p))
 def test_negative_23(self):
  p=copy.deepcopy(self.p)
  p["checks"]["recovery"]=False
  self.assertTrue(validate(p))
 def test_negative_24(self):
  p=copy.deepcopy(self.p)
  p["checks"]["postmortem"]=False
  self.assertTrue(validate(p))
 def test_negative_25(self):
  p=copy.deepcopy(self.p)
  p["owner"]=""
  self.assertTrue(validate(p))
 def test_negative_26(self):
  p=copy.deepcopy(self.p)
  p["environment"]="production"
  self.assertTrue(validate(p))
 def test_negative_27(self):
  p=copy.deepcopy(self.p)
  p["incident_id"]=""
  self.assertTrue(validate(p))
 def test_negative_28(self):
  p=copy.deepcopy(self.p)
  p["severity"]="SEV0"
  self.assertTrue(validate(p))
 def test_negative_29(self):
  p=copy.deepcopy(self.p)
  p["approved"]=false
  self.assertTrue(validate(p))
 def test_negative_30(self):
  p=copy.deepcopy(self.p)
  p["independent_recovery_verified"]=false
  self.assertTrue(validate(p))
 def test_negative_31(self):
  p=copy.deepcopy(self.p)
  p["corrective_actions_owned"]=false
  self.assertTrue(validate(p))
 def test_negative_32(self):
  p=copy.deepcopy(self.p)
  p["destructive_action"]=true
  self.assertTrue(validate(p))
 def test_negative_33(self):
  p=copy.deepcopy(self.p)
  p["checks"]=null
  self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
python3 acceptance_gate.py healthy.json
python3 -m unittest -v test_acceptance_gate.py
```

Expected PASS and **35 authored tests**. Runtime execution is not claimed; this is a synthetic attestation check, not independent verification of live incident readiness.

## 24 hands-on exercises

1. Inventory service dependencies.
2. Assign incident command.
3. Validate on-call escalation.
4. Define SEV1/2/3 policy.
5. Document eligible SLI traffic.
6. Baseline API availability.
7. Baseline p99 latency.
8. Baseline data freshness.
9. Inspect multiwindow burn alerts.
10. Verify Alertmanager staging route.
11. Correlate Grafana metrics.
12. Correlate Loki logs.
13. Inspect Tempo trace.
14. Inspect Kubernetes events.
15. Inspect PostgreSQL waits.
16. Inspect Redis hot keys.
17. Inspect Kafka consumer age.
18. Inspect Elasticsearch rejections.
19. Inspect Snowflake task freshness.
20. Create two causal hypotheses.
21. Simulate approved canary regression.
22. Rehearse safe rollback.
23. Verify independent recovery.
24. Conduct blameless acceptance review.

## 24 production failure scenarios

1. **API outage:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
2. **High p99 latency:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
3. **Regional partial outage:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
4. **PostgreSQL pool exhaustion:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
5. **PostgreSQL replica lag:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
6. **Redis hot-key overload:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
7. **Kafka consumer lag:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
8. **Kafka duplicate replay:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
9. **Elasticsearch rejected queries:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
10. **Elasticsearch storage bottleneck:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
11. **Snowflake stale CDC:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
12. **Kubernetes OOMKilled:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
13. **Kubernetes bad readiness probe:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
14. **OpenTelemetry missing spans:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
15. **Prometheus absent series:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
16. **Alertmanager missed page:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
17. **False-positive page:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
18. **Incorrect SEV classification:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
19. **Conflicting incident updates:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
20. **Sensitive data in evidence:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
21. **Unapproved mitigation:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
22. **Rollback schema incompatibility:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
23. **Recovery declared too early:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.
24. **Unowned postmortem action:** establish customer impact, severity, evidence, mitigation ownership and recovery checks.

## Eight production runbooks

1. **Declare and command: verify impact, severity, commander, communications and UTC timeline.**
2. **Triage and correlate: inspect SLO burn, RED/USE, logs, traces and release history.**
3. **Database and pipeline investigation: PostgreSQL, Redis, Kafka, search and Snowflake evidence.**
4. **Escalation and communications: primary/secondary, service owners and verified stakeholder updates.**
5. **Mitigation decision: document reversible action, approval, risk, rollback and guardrails.**
6. **Rollback and data integrity: staging deployment recovery with stateful consistency checks.**
7. **Recovery acceptance: independent user SLIs, data freshness, stability window and no missing telemetry.**
8. **Postmortem and follow-up: blameless timeline, corrective owners, deadlines and effectiveness checks.**

## 100-point enterprise reliability acceptance

| Domain | Points |
|---|---:|
| Detection, severity and on-call | 20 |
| Metrics, logs, traces and dependency triage | 20 |
| Incident command and communications | 20 |
| Safe mitigation, rollback and recovery | 20 |
| Postmortem, corrective actions and evidence | 20 |
| **Total** | **100** |

Recommended passing score: 85/100. Production sign-off requires witnessed staging game day, tested paging, observed independent recovery, specialist approval and corrective-action ownership.

**Companion:** [Chapter 080 capstone lab](labs/080-enterprise-incident-response-troubleshooting-reliability-acceptance-capstone-lab.md).

**Part 16 complete. Next:** Chapter 081 — Observability as Code Foundations, Repository Architecture and GitOps Workflows (Part 17).
