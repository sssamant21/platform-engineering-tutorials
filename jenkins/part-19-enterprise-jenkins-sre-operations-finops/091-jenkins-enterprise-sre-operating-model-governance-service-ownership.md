# Chapter 091 — Jenkins Enterprise SRE Operating Model, Governance and Service Ownership

**Part 19 — Enterprise Jenkins SRE Operations and FinOps**  
**Audience:** Jenkins platform SRE/DBRE, DevOps, application owners, security, compliance, finance and incident commanders.  
**Prerequisites:** Chapters 001–090; Git, Python 3, optional Jenkins staging controller and Prometheus/Grafana.

## 1. Learning outcomes

Define a sustainable enterprise Jenkins service with explicit ownership, service tiers, measurable SLIs/SLOs, error budgets, on-call coverage, incident escalation, changes, risk management, cost accountability, audit evidence and operational readiness gates. Build a small **executable governance validator** and an auditable service catalog. The lab is safe and offline; no production controller access is required.

## 2. Reference operating model

```text
Business service owners ── requirements / impact / criticality
           |
Platform product owner ── roadmap / budget / lifecycle
           |
Jenkins SRE on-call ── SLOs / alerts / incidents / capacity
           |
DevOps/CI users ── pipeline code / tests / artifacts
           |
Security & compliance ── identity / secrets / policy / audit
           |
Infra/Cloud & DBRE ── compute / storage / network / stateful recovery
           |
Governance forum ── risk acceptance / changes / investment
```

**Service boundary:** Jenkins is the CI orchestration service, not the owner of every application pipeline's correctness. The Jenkins platform team owns controller uptime, supported agents, platform plugins, backup/recovery and platform-level security. Pipeline owners own their Jenkinsfiles, build dependencies, tests, release approval and downstream deployment effects. Shared failures need joint incident ownership.

## 3. Service catalog and tiers

A catalog entry must identify service ID, tier, environment, platform owner, business owner, on-call route, dependencies, RTO/RPO, SLOs, cost center, data classification, maintenance window and DR runbook.

| Tier | Example | Operating expectation |
|---|---|---|
| T0 | Enterprise release orchestration | 24x7 on-call, explicit DR and strict change approval |
| T1 | Critical production CI | rapid escalation and tested restore |
| T2 | Team CI | business-hours support or defined coverage |
| T3 | Sandbox/training | best effort with cost and retention limits |

Tier assignments must be approved based on business impact; example targets below are **illustrative**, not universal defaults.

## 4. Responsibility and RACI

| Activity | Platform SRE | Pipeline owner | Security | Infra/DBRE | Service owner |
|---|---|---|---|---|---|
| Controller health and upgrades | A/R | I | C | C | I |
| Pipeline logic and build failures | C | A/R | I | I | I |
| Credentials/RBAC policy | R | C | A | I | I |
| Persistent storage/backup | A | I | C | R | I |
| DR acceptance | R | C | C | R | A |
| Capacity and cost | R | C | I | R | A |
| Incident command | R | C | C | C | A |

A = accountable; R = responsible; C = consulted; I = informed. Exactly one accountable owner per activity should be confirmed in the local operating agreement.

## 5. SLIs, SLOs and error budgets

Measure user-impacting availability, not only controller process uptime. Recommended candidates:
- **UI/API availability:** successful authenticated health and critical API probes.
- **Job scheduling latency:** queue wait from runnable to executor start, segmented by job tier.
- **Agent provisioning success:** provisioned and connected within an agreed threshold.
- **Pipeline infrastructure failure rate:** failures attributable to Jenkins, plugins, agents or platform, excluding application test failures.
- **Recovery:** backup restore validation, observed RTO and RPO.
- **Security and operational readiness:** credential rotation, unsupported plugin age and audit evidence completeness.

Example **30-day** availability SLO 99.9% allows `30 × 24 × 60 × (1 - 0.999) = 43.2 minutes` of unavailable time. A 99.95% target allows 21.6 minutes. Use consistent calendar windows and measurement rules. Exclusions must be documented, not silently removed.

### PromQL reference patterns

```promql
sum(rate(jenkins_platform_probe_success_total{result="success"}[5m]))
/
clamp_min(sum(rate(jenkins_platform_probe_success_total[5m])), 1)
```

This assumes a **custom** probe counter with a `result` label; it is not a standard Jenkins metric. Define the instrumentation and label cardinality before deploying.

```promql
histogram_quantile(
  0.95,
  sum by (le, tier) (rate(jenkins_queue_wait_seconds_bucket[5m]))
)
```

The queue histogram is also a **proposed custom metric**. Confirm exporter coverage or instrument it before using this query.

## 6. Error budget policy

| Remaining budget | Example action |
|---|---|
| > 50% | normal controlled delivery |
| 25–50% | review risky changes, prioritize reliability |
| 0–25% | restrict nonessential production changes |
| exhausted | freeze discretionary changes, prioritize incident remediation and leadership review |

Exceptions require documented risk acceptance and should never block urgent security fixes or restoration work.

## 7. On-call and incident lifecycle

1. Detect using actionable alerts tied to user-impacting SLIs.
2. Triage controller, executor queue, agents, plugins, SCM, DNS, storage and credentials.
3. Assign incident commander, technical lead and communications lead for major incidents.
4. Declare severity using business impact, not just CPU utilization.
5. Mitigate safely: stop unsafe rollout, preserve controller single-writer and avoid blind restarts.
6. Escalate to Infra/DBRE, security or pipeline owners as appropriate.
7. Publish stakeholder updates at the agreed cadence.
8. Recover and validate representative critical pipelines and artifacts.
9. Record timeline, RCA, contributing factors and corrective actions.
10. Track COAs with owners, due dates and verification evidence.

## 8. Change, security and lifecycle governance

- Every production controller/plugin/JCasC change has an owner, reviewed diff, backup checkpoint, rollback, test plan and change record.
- Core, Java and plugin compatibility is validated in staging; unsupported versions require tracked exceptions.
- Privileged Jenkins credentials use approved secret managers and least privilege. Restrict untrusted PR execution from accessing production secrets.
- Quarterly access reviews verify administrator grants, service identities, orphaned agents and pipeline privileges.
- Track audit retention, signed artifacts where required, immutable logs and evidence access controls.
- Review RPO/RTO, storage integrity and restore drills periodically.

## 9. FinOps and capacity ownership

Attribute controller, agent compute, storage, network egress, artifact retention and observability costs to environments and cost centers. Track queue pressure, executor saturation, ephemeral agent idle time and cost per successful build **with workload normalization**. Do not optimize cost by reducing resilience below approved service tiers. Tag resources and budget owners; review idle agents, cache effectiveness and retention policies.

## 10. Executable service catalog and governance validator

Create `catalog/jenkins-services.json`:

```json
{
  "services": [
    {
      "id": "jenkins-staging",
      "tier": "T2",
      "environment": "staging",
      "platform_owner": "platform-sre",
      "business_owner": "devex",
      "oncall_route": "platform-sre-oncall",
      "cost_center": "engineering",
      "data_classification": "internal",
      "rto_minutes": 240,
      "rpo_minutes": 60,
      "availability_slo": 0.999,
      "dr_runbook": "runbooks/jenkins-staging-dr.md",
      "last_restore_test": "2026-10-01"
    }
  ]
}
```

Create `scripts/validate_catalog.py`:

```python
#!/usr/bin/env python3
import json
import sys
from datetime import date
from pathlib import Path

REQUIRED = ("id", "tier", "environment", "platform_owner", "business_owner",
            "oncall_route", "cost_center", "data_classification", "rto_minutes",
            "rpo_minutes", "availability_slo", "dr_runbook", "last_restore_test")

def validate(document):
    errors = []
    services = document.get("services")
    if not isinstance(services, list) or not services:
        return ["services must be a nonempty list"]
    seen = set()
    for i, svc in enumerate(services):
        prefix = f"services[{i}]"
        if not isinstance(svc, dict):
            errors.append(f"{prefix}: expected object")
            continue
        for key in REQUIRED:
            if key not in svc or svc[key] in (None, ""):
                errors.append(f"{prefix}: missing {key}")
        sid = svc.get("id")
        if sid in seen:
            errors.append(f"{prefix}: duplicate id {sid}")
        seen.add(sid)
        if svc.get("tier") not in ("T0", "T1", "T2", "T3"):
            errors.append(f"{prefix}: invalid tier")
        for field in ("rto_minutes", "rpo_minutes"):
            value = svc.get(field)
            if type(value) is not int or value <= 0:
                errors.append(f"{prefix}: {field} must be positive integer")
        slo = svc.get("availability_slo")
        if type(slo) not in (int, float) or not 0 < slo <= 1:
            errors.append(f"{prefix}: invalid availability_slo")
        try:
            date.fromisoformat(svc["last_restore_test"])
        except (KeyError, ValueError, TypeError):
            errors.append(f"{prefix}: invalid last_restore_test")
    return errors

if __name__ == "__main__":
    issues = validate(json.loads(Path(sys.argv[1]).read_text()))
    if issues:
        print("GOVERNANCE FAIL", *issues, sep="\n")
        sys.exit(1)
    print("GOVERNANCE PASS: catalog schema only")
```

Run:

```bash
python3 scripts/validate_catalog.py catalog/jenkins-services.json
```

The validator checks **schema and basic field constraints only**; it does not verify actual on-call coverage, DR tests, SLO measurements or regulatory compliance.

## 11. Governance-as-code CI

```groovy
pipeline {
  agent { label 'governance-validation' }
  options { timestamps(); timeout(time: 10, unit: 'MINUTES') }
  stages {
    stage('Checkout') { steps { checkout scm } }
    stage('Validate service catalog') {
      steps { sh 'python3 scripts/validate_catalog.py catalog/jenkins-services.json' }
    }
  }
}
```

Use pinned trusted agents and a protected branch. Add code-owner review, automated schema tests, policy checks and evidence publishing in the production workflow.

## 12. Twenty troubleshooting and governance failure scenarios

| # | Failure | Investigation |
|---|---|---|
| 01 | No platform owner | catalog |
| 02 | Missing pipeline owner | RACI |
| 03 | Unrouted critical alert | on-call |
| 04 | Alert noise hides outage | alert quality |
| 05 | SLO measures only process uptime | SLI design |
| 06 | Pipeline test failures inflate platform SLI | failure attribution |
| 07 | Queue p95 grows | executor capacity |
| 08 | Agent provision failure | cloud/quota/network |
| 09 | Unsupported plugin | compatibility inventory |
| 10 | RBAC privilege creep | access review |
| 11 | Backup exists but restore fails | DR drill |
| 12 | Unowned credential | secret inventory |
| 13 | Unapproved production change | change audit |
| 14 | Error budget exhausted | policy |
| 15 | False SLO burn alert | instrumentation |
| 16 | Missing incident commander | escalation |
| 17 | RCA lacks actionable COA | postmortem |
| 18 | Cost center absent | tagging |
| 19 | Idle agents drive spend | utilization |
| 20 | Audit evidence missing | retention |

## 13. Six production runbooks

### A. Ownership or on-call gap
Identify impacted tier and owner, page fallback team, assign accountable owner, update catalog and test paging.

### B. SLO burn or service degradation
Validate telemetry, identify user impact, declare severity, mitigate queue/agent/controller bottleneck and track budget.

### C. Controller outage
Check dependencies, storage and logs, preserve one active writer, restore from tested backup if required and validate synthetic CI.

### D. Unapproved privileged change
Freeze high-risk changes, preserve audit trail, rotate exposed credentials if applicable and coordinate security review.

### E. Cost anomaly
Identify tags, agent lifecycle, queue and storage growth, validate demand before rightsizing and preserve SLO protections.

### F. Governance audit failure
Record missing evidence, owners and deadline; generate authoritative proof, remediate control gap and re-review.

## 14. 100-point acceptance

| Domain | Points |
|---|---:|
| Service catalog and ownership | 20 |
| SLI/SLO/error-budget governance | 20 |
| Incident response and on-call | 20 |
| Change, access and lifecycle controls | 15 |
| Capacity and FinOps accountability | 15 |
| Evidence, DR and review sign-off | 10 |
| **Total** | **100** |

Suggested pass 85/100 plus mandatory gates: named platform owner, working escalation route, defined service SLO, reviewed DR plan, privileged-access governance and approved change process. Do not mark unexecuted checks as passed.

## 15. Evidence template

```text
UTC / service / tier:
Platform owner / business owner / pipeline owner:
On-call route and escalation test:
SLIs, SLOs, error budget window:
Incident and change review:
Jenkins core/Java/plugins/JCasC:
Backup RTO/RPO and restore evidence:
Security and RBAC review:
Capacity/cost center and budget:
20 scenarios / six runbooks:
Score / RCA / COA / reviewer:
```

**Companion:** [Chapter 091 hands-on lab](labs/091-jenkins-enterprise-sre-operating-model-governance-service-ownership-check.md).  
**Next:** Chapter 092 — Jenkins SLOs, Error Budgets and Enterprise Reliability Governance.
