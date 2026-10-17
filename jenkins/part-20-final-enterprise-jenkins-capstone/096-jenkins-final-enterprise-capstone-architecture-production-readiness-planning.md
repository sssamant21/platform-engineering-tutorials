# Chapter 096 — Jenkins Final Enterprise Capstone Architecture and Production Readiness Planning

**Part 20 — Final Enterprise Jenkins Capstone**  
**Audience:** Jenkins SRE/DBRE, platform architects, DevOps, security, change managers and service owners.  
**Prerequisites:** Chapters 001–095; Python 3; optional disposable Jenkins staging cluster, Kubernetes/EKS/AKS and Git.

## 1. Mission

Design and review a **production-ready enterprise Jenkins platform** before deployment. Integrate all previous parts: architecture, controllers/agents, GitOps/JCasC, pipelines, Kubernetes, security, observability, scaling, DR, Terraform/Ansible, SLOs and FinOps. Produce architecture decision records, threat model, readiness gates, a safe lab validation and a signed go/no-go packet.

**Safety:** This chapter provides local synthetic checks and a staging validation plan. Passing offline checks does not certify production readiness.

## 2. Reference architecture

```text
              Enterprise IdP (SSO/MFA)
                        |
SCM / PR / webhook ---> ingress / TLS / WAF
                        |
                 Jenkins controller
                  JCasC + RBAC + plugins
                        |
             agent provisioning boundary
             /             |             \
       K8s ephemeral   VM agents    isolated release pool
             \             |             /
                artifact repository
                     |       |
              SBOM/provenance  deploy approval
                        |
               EKS / AKS / cloud
                        |
 Prometheus/Grafana + logs + audit + backup/DR
                        |
 Terraform / Ansible / GitOps + service ownership
```

Controllers must not share the same writable JENKINS_HOME. Multi-controller designs require explicit separation and controlled routing, not simultaneous writers. Keep credentials away from untrusted PR builds.

## 3. Architecture decisions (ADRs)

Document these decisions and alternatives:
1. Single-controller vs multiple isolated controllers, blast radius and upgrade cadence.
2. Kubernetes vs VM agents; ephemeral vs static workloads.
3. Storage class, IOPS, backup consistency, encryption and recovery.
4. IdP, RBAC, folder isolation and emergency access.
5. SCM webhook verification and untrusted PR boundaries.
6. JCasC, plugin version pinning and compatibility matrix.
7. Artifact retention, provenance and promotion.
8. Cloud region, network boundaries and egress.
9. Observability, SLOs and incident ownership.
10. Terraform/Ansible/GitOps ownership and drift policy.
11. RTO/RPO and DR strategy.
12. Cost attribution, quotas and capacity headroom.

Each ADR needs context, options, chosen decision, consequences, owner and review date.

## 4. Service requirements and SLOs

Define availability, authenticated API success, critical-job scheduling latency, agent provisioning latency, CI platform failure rate and restore validation. Example targets (illustrative only):

| Objective | Example target | Validation |
|---|---|---|
| Authenticated API | 99.9% over rolling 30 days | synthetic probes |
| Critical queue wait | p95 under 120s | workload-class histogram |
| Agent provisioning | p95 under 180s | synthetic launch |
| RTO | 240 minutes | restore drill |
| RPO | 60 minutes | backup timestamp |
| Cost | agreed budget and cost center | billing reconciliation |

The owner approves targets and definitions. Do not confuse controller uptime with successful CI delivery.

## 5. Security and supply-chain blueprint

- Enforce SSO/MFA and least-privilege RBAC.
- Disable controller executors and anonymous administration.
- Use short-lived workload identities, external secrets and rotation.
- Separate untrusted PR and production release agents.
- Avoid privileged containers and Docker socket mounts by default.
- Pin Jenkins LTS, Java, plugins, base images and dependencies.
- Require protected branches, signed/provenance-linked artifacts and approved promotion.
- Preserve encrypted backups, immutable audit records and emergency access procedures.
- Validate data residency, retention and applicable organization controls.

## 6. Infrastructure and configuration ownership

```text
Terraform: networks, compute, IAM, storage, cluster resources
Ansible: OS baseline, VM configuration and host prerequisites
JCasC: Jenkins security realm, authorization, clouds and platform settings
Pipeline-as-code: jobs, tests, artifacts and approved deployments
GitOps: Kubernetes application/workload declarations
```

Do not allow overlapping writers to the same resource. Use isolated state backends, locked state, plan review and separate plan/apply identities.

## 7. Capacity and FinOps design

Estimate concurrency with observed arrivals and runtime, then validate burst patterns and p95 queue latency. Track controller heap/GC, agent idle time, node packing, image pulls, artifact growth, backup storage, egress and monitoring spend. Allocate shared overhead transparently; reject rightsizing that violates SLO or DR gates.

## 8. Recovery and upgrade readiness

Define backup scope (JENKINS_HOME, JCasC, plugin list, secrets/key custody, jobs, credentials metadata, external integrations), encryption, restore compatibility and RTO/RPO. Run restore tests on an isolated controller with no shared writable home. Validate representative pipelines, agents, RBAC, artifact access and SCM after recovery. Require a tested rollback path for core/Java/plugin upgrades.

## 9. Executable architecture-readiness contract

Save `architecture/readiness.json`:

```json
{
  "service": "jenkins-staging",
  "environment": "staging",
  "platform_owner": "platform-sre",
  "business_owner": "devex",
  "oncall_route": "platform-sre-oncall",
  "controller_writers": 1,
  "controller_executors": 0,
  "sso_mfa": true,
  "anonymous_admin": false,
  "untrusted_pr_prod_secrets": false,
  "encrypted_backups": true,
  "restore_tested": true,
  "rto_minutes": 240,
  "rpo_minutes": 60,
  "slo_target": 0.999,
  "cost_center": "engineering",
  "change_approval": true,
  "audit_retention": true,
  "artifact_provenance": true,
  "state_locking": true,
  "rollback_documented": true
}
```

Save `scripts/readiness_gate.py`:

```python
#!/usr/bin/env python3
import json
import sys
from pathlib import Path

TRUE_FIELDS = ("sso_mfa", "encrypted_backups", "restore_tested",
               "change_approval", "audit_retention", "artifact_provenance",
               "state_locking", "rollback_documented")
FALSE_FIELDS = ("anonymous_admin", "untrusted_pr_prod_secrets")
TEXT_FIELDS = ("service", "environment", "platform_owner",
               "business_owner", "oncall_route", "cost_center")

def check(data):
    errors = []
    for key in TRUE_FIELDS:
        if data.get(key) is not True:
            errors.append(f"{key} must be true")
    for key in FALSE_FIELDS:
        if data.get(key) is not False:
            errors.append(f"{key} must be false")
    for key in TEXT_FIELDS:
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"{key} missing")
    for key, expected in (("controller_writers", 1), ("controller_executors", 0)):
        if type(data.get(key)) is not int or data[key] != expected:
            errors.append(f"{key} must equal {expected}")
    for key in ("rto_minutes", "rpo_minutes"):
        if type(data.get(key)) is not int or data[key] <= 0:
            errors.append(f"{key} must be positive integer")
    slo = data.get("slo_target")
    if type(slo) not in (float, int) or not 0 < slo < 1:
        errors.append("slo_target invalid")
    return errors

if __name__ == "__main__":
    data = json.loads(Path(sys.argv[1]).read_text())
    errors = check(data)
    if errors:
        print("NO-GO: synthetic contract", *errors, sep="\n")
        sys.exit(1)
    print("GO: synthetic contract only; real evidence still required")
```

```bash
python3 scripts/readiness_gate.py architecture/readiness.json
```

The checker tests a declared JSON fixture, **not live Jenkins, IAM, cloud storage or backup controls**. Production go/no-go requires authoritative evidence for every field.

## 10. Negative test

```bash
cp architecture/readiness.json /tmp/jenkins-architecture-unsafe.json
python3 - <<'PY'
import json
p = "/tmp/jenkins-architecture-unsafe.json"
with open(p) as f:
    d = json.load(f)
d["controller_writers"] = 2
d["untrusted_pr_prod_secrets"] = True
d["restore_tested"] = False
with open(p, "w") as f:
    json.dump(d, f)
PY
if python3 scripts/readiness_gate.py /tmp/jenkins-architecture-unsafe.json; then
  echo "FAIL: unsafe architecture accepted"; exit 1
else
  echo "PASS: unsafe architecture denied"
fi
```

## 11. Jenkins validation pipeline

```groovy
pipeline {
  agent { label 'governance-validation' }
  options { timestamps(); timeout(time: 10, unit: 'MINUTES') }
  stages {
    stage('Checkout') { steps { checkout scm } }
    stage('Architecture contract') {
      steps { sh 'python3 scripts/readiness_gate.py architecture/readiness.json' }
    }
  }
}
```

Use a pinned trusted agent with no production write credentials. Require CODEOWNERS approval for changes to readiness policy.

## 12. Twenty-four architecture labs

1. Define business service, users and impact.
2. Assign tier, platform owner and on-call.
3. Diagram controller and trust boundaries.
4. Define controller isolation and single-writer rule.
5. Design Kubernetes/VM agent pools.
6. Design SCM/webhook ingress and TLS.
7. Define IdP, SSO/MFA and RBAC.
8. Define credential and workload identity model.
9. Define JCasC and plugin version policy.
10. Define artifact/SBOM/provenance controls.
11. Define Terraform/Ansible/GitOps ownership.
12. Design state backend, locking and approval.
13. Define controller and agent SLIs.
14. Calculate SLO/error budget.
15. Define queue and agent capacity targets.
16. Forecast cost and ownership.
17. Define backup scope and key custody.
18. Define RTO/RPO and restore drill.
19. Define upgrade and rollback acceptance.
20. Define observability and incident escalation.
21. Write 12 ADRs and threat model.
22. Execute offline readiness checker.
23. Execute unsafe negative test.
24. Produce architecture review and go/no-go packet.

## 13. Twenty architecture failure scenarios

| # | Scenario | Guardrail |
|---|---|---|
| 01 | Two controllers write one home | hard stop |
| 02 | Controller runs untrusted builds | zero executors |
| 03 | Anonymous admin access | RBAC gate |
| 04 | SSO/MFA unavailable | audited break-glass |
| 05 | PR sees production secrets | trust isolation |
| 06 | Privileged agent escapes | pod security |
| 07 | Plugin incompatible with Java | staging matrix |
| 08 | JCasC invalid | schema/test |
| 09 | Terraform state unlocked | backend policy |
| 10 | Drift auto-applies destructive plan | approval |
| 11 | Storage IOPS bottleneck | sizing |
| 12 | Controller OOM | JVM capacity |
| 13 | Queue SLO breach | pool sizing |
| 14 | Agent image pull outage | fallback |
| 15 | SCM webhook spoofing | signature validation |
| 16 | Artifact provenance missing | promotion block |
| 17 | Backup unusable | restore drill |
| 18 | Recovery exceeds RTO | DR remediation |
| 19 | Unattributed cloud cost | FinOps tags |
| 20 | Architecture sign-off missing | no-go |

## 14. Eight production runbooks

### A. Architecture no-go
Stop rollout, identify failed mandatory gate, assign owner and retest before approval.

### B. Controller/storage outage
Protect single-writer invariant, inspect storage and controller logs, restore isolated compatible instance if required.

### C. Agent/queue capacity incident
Check executor pressure, Kubernetes scheduling, quotas and image pulls; mitigate without weakening trust isolation.

### D. Identity or secret breach
Isolate affected jobs, revoke/rotate credentials, preserve audit and involve security incident command.

### E. Plugin/JCasC upgrade failure
Rollback tested versions/configuration, verify critical pipelines, record RCA/COA.

### F. Terraform state/drift incident
Freeze applies, inspect state lock and audit, recover through approved procedure, never blind force-unlock.

### G. DR acceptance failure
Document observed RTO/RPO and missing dependencies, correct runbook and repeat restore.

### H. Cost or SLO regression
Compare baseline and post-change signals, revert risky optimization and reconcile cloud cost.

## 15. 100-point architecture acceptance

| Domain | Points |
|---|---:|
| Architecture, ADRs and service ownership | 20 |
| Controller, agents and infrastructure design | 20 |
| Identity, secrets and supply-chain controls | 20 |
| SLOs, capacity, observability and FinOps | 15 |
| Backup, DR, upgrade and rollback | 15 |
| Tests, evidence and review sign-off | 10 |
| **Total** | **100** |

Suggested pass **85/100** plus mandatory gates: approved ownership, single-writer architecture, no untrusted PR secrets, supported platform stack, tested restore, approved SLO, rollback and change governance. **Synthetic fixture success alone is insufficient.**

## 16. Evidence template

```text
UTC / service / tier:
Architecture diagram and 12 ADRs:
Owners and on-call:
Controller/agent topology:
SSO/MFA/RBAC/secret isolation:
JCasC/plugins/core/Java:
Terraform/Ansible/GitOps ownership:
SLO/error budget and queue capacity:
Cost model and billing owner:
Backup/restore/RTO/RPO:
Change/rollback/DR:
24 labs / 20 failures:
Score / mandatory gates / reviewer / RCA / COA:
```

**Companion:** [Chapter 096 hands-on lab](labs/096-jenkins-final-enterprise-capstone-architecture-production-readiness-planning-check.md).  
**Next:** Chapter 097 — Jenkins Enterprise Platform Deployment and CI/CD Integration Capstone.
