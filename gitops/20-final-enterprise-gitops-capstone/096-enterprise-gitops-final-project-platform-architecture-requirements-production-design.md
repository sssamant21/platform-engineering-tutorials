# Chapter 096 — Enterprise GitOps Final Project: Platform Architecture, Requirements and Production Design

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 20:** Final Enterprise GitOps Capstone  
**Chapter:** 096 / 100  
**Audience:** Platform Architects, SRE, DBRE, Security, Cloud Engineering and Release Engineering

> **Scope:** This is a design-first, hands-on reference project for an approved isolated lab. Do not execute production provisioning, credential changes or cluster mutations without environment-specific review and change authorization.

## 1. Project mission

Design a production-ready enterprise GitOps delivery platform from business requirements to architecture review. The reference system must support multi-environment deployments, protected GitLab CI/CD, signed immutable artifacts, Helm packaging, Argo CD reconciliation, least-privilege security, secrets, progressive delivery, SLO monitoring, cost governance and recoverable stateful services.

This chapter delivers the **blueprint**; Chapters 097–100 will implement, operate, stress-test and assess the platform.

## 2. Scenario and assumptions

A fictional enterprise deploys a stateless API plus PostgreSQL-backed transactional service across development, staging and production. Engineering teams require auditable approvals, environment isolation, reproducible releases, fast rollback, controlled infrastructure changes, reliable multi-AZ service and a tested secondary-region recovery plan.

Assumptions are illustrative, not claims about a real organization. Cloud provider and sizing must be selected using actual quotas, latency, compliance, workload profile and cost data.

## 3. Reference architecture

```text
 Developers --> protected GitLab repositories
                         |
               CI tests / SAST / SBOM
                         |
               build + sign OCI images
                         |
                  immutable registry
                         |
          approved GitOps config promotion
                         |
          +--------------+--------------+
          |                             |
      Argo CD dev/staging           Argo CD production
          |                             |
   namespace / policy          AppProjects / policy
          |                             |
   Helm application               Helm application
                                        |
                               ingress / TLS / DNS
                                        |
                             API + PostgreSQL primary
                                        |
                            backup + replica + DR region
                                        |
                        independent telemetry + SLO alerts
```

**Design rule:** CI builds and validates artifacts; Git holds desired deployment state; Argo CD reconciles approved revisions. Prevent CI from bypassing GitOps with direct, unrestricted production cluster writes.

## 4. Requirements matrix

| ID | Requirement | Acceptance test |
|---|---|---|
| FR-01 | Deploy approved image digest via GitOps | Commit traceable to running digest |
| FR-02 | Promote dev → staging → prod | Signed approvals and evidence |
| FR-03 | Roll back failed release | Verified previous revision and data compatibility |
| FR-04 | Support multiple teams | AppProject and namespace isolation |
| FR-05 | Provision reproducibly | Pinned IaC and Helm version |
| NFR-01 | Availability and latency | Business-approved SLO and synthetic checks |
| NFR-02 | Security | Least privilege, secret isolation, provenance |
| NFR-03 | Auditability | Git, CI, Argo CD and cloud audit correlation |
| NFR-04 | Recoverability | Measured RPO/RTO, backup restore and fencing |
| NFR-05 | Cost | Capacity model and budget alert thresholds |

SLO and RPO/RTO numbers must be defined with business owners, not invented from a reference architecture.

## 5. Recommended repository structure

```text
enterprise-gitops/
  README.md
  docs/
    architecture.md
    requirements.md
    threat-model.md
    slo-rpo-rto.md
    adr/
    runbooks/
  infrastructure/
    terraform/
      modules/
      environments/{dev,staging,prod}/
  platform/
    bootstrap/
    argocd/
      projects/
      applicationsets/
    policies/
    external-secrets/
    observability/
  applications/
    synthetic-api/
      chart/
      tests/
  environments/
    dev/
    staging/
    prod/
  .gitlab-ci.yml
  CODEOWNERS
```

Prefer a protected GitOps configuration repository and separate application source repositories where organizational controls require different write permissions. Protect production overlays from application build jobs.

## 6. Example AppProject boundary

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: team-a
  namespace: argocd
spec:
  description: Restricted team A applications
  sourceRepos:
    - https://git.example.invalid/platform/team-a-gitops.git
  destinations:
    - namespace: team-a-*
      server: https://kubernetes.default.svc
  clusterResourceWhitelist: []
  namespaceResourceBlacklist:
    - group: ""
      kind: ResourceQuota
```

**Review carefully:** wildcard namespaces, source restrictions and cluster-scoped permissions must match the installed Argo CD version and actual policy. This example is a starting point, not a complete security boundary; pair with Kubernetes RBAC, admission policies, network isolation and protected Git.

## 7. Architecture decisions and tradeoffs

| Decision | Option A | Option B | Choose based on |
|---|---|---|---|
| Argo CD topology | Central management | Per-cluster instances | Blast radius, tenancy, network |
| Environment isolation | Namespace | Dedicated cluster/account | Risk and compliance |
| Secrets | External Secrets | SOPS-encrypted Git | Key custody, audit, recovery |
| Rollout | Rolling update | Canary/blue-green | SLO, traffic control |
| Data DR | Replication | Backup/PITR | RPO, consistency, budget |
| Artifact availability | Single registry | Replicated registry | Regional resilience |
| Cloud | EKS | AKS/GKE | Workload, compliance, skill, cost |

## 8. Design lab preflight

```bash
export LAB_NS=enterprise-gitops-lab
kubectl config current-context
kubectl get nodes -o wide
kubectl -n "$LAB_NS" get deploy,pods,svc --ignore-not-found
helm version
git --version
```

These commands are read-only inspection aids. Design artifacts should be reviewed before any provisioning.

## 9. Hands-on architecture labs (18)

Each lab must produce a named artifact, review owner, expected evidence, rollback consideration and acceptance decision.

### Lab 01 — Stakeholder and service inventory

**Design exercise:** Document business service, customers, environments, critical dependencies and owners.

```bash
kubectl config get-contexts
kubectl get namespaces
```

**Acceptance:** Signed inventory and RACI. **Safety:** read-only commands unless an explicitly approved disposable lab task is separately authorized.

### Lab 02 — Functional requirements

**Design exercise:** Write service deployment, promotion, rollback, audit and multi-tenant requirements.

```bash
git status --short
find . -maxdepth 2 -type f | head -30
```

**Acceptance:** Traceable functional requirements. **Safety:** read-only commands unless an explicitly approved disposable lab task is separately authorized.

### Lab 03 — Nonfunctional requirements

**Design exercise:** Specify availability, p95 latency, RPO/RTO, security, cost and compliance acceptance.

```bash
date -u +%FT%TZ
kubectl get nodes -o wide
```

**Acceptance:** Measurable SLO and constraints. **Safety:** read-only commands unless an explicitly approved disposable lab task is separately authorized.

### Lab 04 — GitOps repository design

**Design exercise:** Define platform/app/config separation and environment overlays with CODEOWNERS.

```bash
git branch --show-current
git ls-files | head -40
```

**Acceptance:** Approved repository tree. **Safety:** read-only commands unless an explicitly approved disposable lab task is separately authorized.

### Lab 05 — GitLab governance

**Design exercise:** Plan protected branches, approvals, pipeline permissions, runners and audit retention.

```bash
git log -1 --format='%h %s'
git remote -v
```

**Acceptance:** Separation-of-duties matrix. **Safety:** read-only commands unless an explicitly approved disposable lab task is separately authorized.

### Lab 06 — OCI and Helm supply chain

**Design exercise:** Pin artifact digests, chart versions, signatures and SBOM policy.

```bash
helm version
kubectl -n "$LAB_NS" get deploy -o yaml | grep -E 'image:'
```

**Acceptance:** Reproducible artifact policy. **Safety:** read-only commands unless an explicitly approved disposable lab task is separately authorized.

### Lab 07 — Cluster topology

**Design exercise:** Design EKS/AKS/GKE choice, AZ spread, node pools, quotas, autoscaling and upgrade path.

```bash
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get storageclass
```

**Acceptance:** Topology and capacity plan. **Safety:** read-only commands unless an explicitly approved disposable lab task is separately authorized.

### Lab 08 — Network architecture

**Design exercise:** Document ingress, Gateway API, DNS, private endpoints, egress and NetworkPolicies.

```bash
kubectl -n "$LAB_NS" get svc,ingress,networkpolicy
kubectl get gatewayclass
```

**Acceptance:** Reviewed traffic and trust boundaries. **Safety:** read-only commands unless an explicitly approved disposable lab task is separately authorized.

### Lab 09 — Identity and secrets

**Design exercise:** Plan workload identity, SSO, AppProject RBAC, external secrets and KMS recovery.

```bash
kubectl -n argocd get appprojects
kubectl -n "$LAB_NS" get serviceaccounts
```

**Acceptance:** Least-privilege access design. **Safety:** read-only commands unless an explicitly approved disposable lab task is separately authorized.

### Lab 10 — Argo CD architecture

**Design exercise:** Define controllers, projects, Applications, ApplicationSets, sync waves and multi-cluster ownership.

```bash
kubectl -n argocd get deploy,sts
kubectl -n argocd get applications,applicationsets
```

**Acceptance:** Safe reconciliation ownership. **Safety:** read-only commands unless an explicitly approved disposable lab task is separately authorized.

### Lab 11 — Environment promotion

**Design exercise:** Specify dev/staging/prod gates, change windows, canary and rollback triggers.

```bash
git diff --check
kubectl -n "$LAB_NS" get deploy -o wide
```

**Acceptance:** Release promotion decision table. **Safety:** read-only commands unless an explicitly approved disposable lab task is separately authorized.

### Lab 12 — Observability and SLO

**Design exercise:** Define logs, traces, metrics, GitOps reconciliation SLIs and independent synthetic checks.

```bash
kubectl -n "$LAB_NS" get pods -o wide
kubectl -n argocd get applications -o wide
```

**Acceptance:** SLI source and alert runbook. **Safety:** read-only commands unless an explicitly approved disposable lab task is separately authorized.

### Lab 13 — Data and persistence

**Design exercise:** Select CSI, backup, database consistency and restore strategy for synthetic stateful workload.

```bash
kubectl -n "$LAB_NS" get pvc
kubectl get volumesnapshotclass
```

**Acceptance:** Storage and RPO design. **Safety:** read-only commands unless an explicitly approved disposable lab task is separately authorized.

### Lab 14 — DR and resilience

**Design exercise:** Model AZ/region failures, Git mirror, registry replication, fencing and failback.

```bash
velero backup get
kubectl get nodes -L topology.kubernetes.io/region
```

**Acceptance:** Dependency-aware DR plan. **Safety:** read-only commands unless an explicitly approved disposable lab task is separately authorized.

### Lab 15 — Security threat model

**Design exercise:** Threat-model compromised CI, Git credentials, artifact substitution and overprivileged sync.

```bash
kubectl auth can-i create deployments -n "$LAB_NS"
kubectl -n argocd get appprojects -o wide
```

**Acceptance:** Mitigations and owner mapping. **Safety:** read-only commands unless an explicitly approved disposable lab task is separately authorized.

### Lab 16 — FinOps and capacity

**Design exercise:** Estimate compute, storage, network egress, runners and backup costs; define guardrails.

```bash
kubectl -n "$LAB_NS" get resourcequota,limitrange
kubectl top nodes
```

**Acceptance:** Capacity and cost assumptions. **Safety:** read-only commands unless an explicitly approved disposable lab task is separately authorized.

### Lab 17 — Architecture decision records

**Design exercise:** Publish ADRs on controller topology, secrets, promotion and DR tradeoffs.

```bash
git diff --check
git status --short
```

**Acceptance:** Reviewable ADRs and rejected alternatives. **Safety:** read-only commands unless an explicitly approved disposable lab task is separately authorized.

### Lab 18 — Final design review

**Design exercise:** Walk through security, SRE, data, platform and product signoff with acceptance gates.

```bash
date -u +%FT%TZ
kubectl config current-context
```

**Acceptance:** Signed design and delivery backlog. **Safety:** read-only commands unless an explicitly approved disposable lab task is separately authorized.

## 10. Twenty design and implementation troubleshooting scenarios

| # | Risk or failure | Detection | Resolution design |
|---|---|---|---|
| 1 | Requirements conflict | Architecture review, policy validation, synthetic test or incident signal | Assign owner; specify prevention, containment, recovery and verification gate |
| 2 | Undefined SLO | Architecture review, policy validation, synthetic test or incident signal | Assign owner; specify prevention, containment, recovery and verification gate |
| 3 | Unowned dependency | Architecture review, policy validation, synthetic test or incident signal | Assign owner; specify prevention, containment, recovery and verification gate |
| 4 | Git branch bypass | Architecture review, policy validation, synthetic test or incident signal | Assign owner; specify prevention, containment, recovery and verification gate |
| 5 | Untrusted image | Architecture review, policy validation, synthetic test or incident signal | Assign owner; specify prevention, containment, recovery and verification gate |
| 6 | Mutable Helm chart | Architecture review, policy validation, synthetic test or incident signal | Assign owner; specify prevention, containment, recovery and verification gate |
| 7 | Single-AZ capacity | Architecture review, policy validation, synthetic test or incident signal | Assign owner; specify prevention, containment, recovery and verification gate |
| 8 | Excessive node privilege | Architecture review, policy validation, synthetic test or incident signal | Assign owner; specify prevention, containment, recovery and verification gate |
| 9 | Public API exposure | Architecture review, policy validation, synthetic test or incident signal | Assign owner; specify prevention, containment, recovery and verification gate |
| 10 | DNS dependency loop | Architecture review, policy validation, synthetic test or incident signal | Assign owner; specify prevention, containment, recovery and verification gate |
| 11 | Missing network policy | Architecture review, policy validation, synthetic test or incident signal | Assign owner; specify prevention, containment, recovery and verification gate |
| 12 | Argo CD cross-tenant access | Architecture review, policy validation, synthetic test or incident signal | Assign owner; specify prevention, containment, recovery and verification gate |
| 13 | ApplicationSet fan-out | Architecture review, policy validation, synthetic test or incident signal | Assign owner; specify prevention, containment, recovery and verification gate |
| 14 | Secret leakage | Architecture review, policy validation, synthetic test or incident signal | Assign owner; specify prevention, containment, recovery and verification gate |
| 15 | KMS region mismatch | Architecture review, policy validation, synthetic test or incident signal | Assign owner; specify prevention, containment, recovery and verification gate |
| 16 | Pipeline runner compromise | Architecture review, policy validation, synthetic test or incident signal | Assign owner; specify prevention, containment, recovery and verification gate |
| 17 | Database restore inconsistency | Architecture review, policy validation, synthetic test or incident signal | Assign owner; specify prevention, containment, recovery and verification gate |
| 18 | No writer fencing | Architecture review, policy validation, synthetic test or incident signal | Assign owner; specify prevention, containment, recovery and verification gate |
| 19 | Unmeasured DR RTO | Architecture review, policy validation, synthetic test or incident signal | Assign owner; specify prevention, containment, recovery and verification gate |
| 20 | Cost estimate omitted | Architecture review, policy validation, synthetic test or incident signal | Assign owner; specify prevention, containment, recovery and verification gate |

## 11. Eight operational design runbooks

### RB-01 — Requirements and change control

**Procedure and control:** Collect signed business objectives, record traceability, resolve conflicting requirements and reject scope expansion without review.

**Required evidence:** named operator and approver, exact source revision, timestamps, affected environment, validation result, abort/rollback decision and post-change review.

### RB-02 — Repository and supply-chain governance

**Procedure and control:** Verify protected Git refs, CODEOWNERS, immutable artifacts, signing policy and least-privilege CI identities.

**Required evidence:** named operator and approver, exact source revision, timestamps, affected environment, validation result, abort/rollback decision and post-change review.

### RB-03 — Platform provisioning

**Procedure and control:** Validate IaC plan, cloud quotas, region/AZ design, network and storage prerequisites; apply only after approval.

**Required evidence:** named operator and approver, exact source revision, timestamps, affected environment, validation result, abort/rollback decision and post-change review.

### RB-04 — Argo CD bootstrap

**Procedure and control:** Install version-pinned CRDs, controllers, identity, AppProjects and Applications in dependency order; verify destination restrictions.

**Required evidence:** named operator and approver, exact source revision, timestamps, affected environment, validation result, abort/rollback decision and post-change review.

### RB-05 — Environment promotion

**Procedure and control:** Enforce CI policy, test evidence, staged rollout, progressive delivery checks, rollback and audit trail.

**Required evidence:** named operator and approver, exact source revision, timestamps, affected environment, validation result, abort/rollback decision and post-change review.

### RB-06 — Security and secrets response

**Procedure and control:** Contain compromised credentials, rotate through approved vault, inspect audit evidence and verify workload identity boundaries.

**Required evidence:** named operator and approver, exact source revision, timestamps, affected environment, validation result, abort/rollback decision and post-change review.

### RB-07 — Backup and disaster recovery

**Procedure and control:** Validate restore point, Git mirror, registry and KMS availability; recover in isolated region and fence old writer before promotion.

**Required evidence:** named operator and approver, exact source revision, timestamps, affected environment, validation result, abort/rollback decision and post-change review.

### RB-08 — Architecture acceptance

**Procedure and control:** Review scorecard, test matrix, SLOs, owners, residual risks, operational handoff and release signoff.

**Required evidence:** named operator and approver, exact source revision, timestamps, affected environment, validation result, abort/rollback decision and post-change review.

## 12. Architecture acceptance scorecard (100 points)

| Domain | Points |
|---|---:|
| Business requirements and traceability | 15 |
| GitLab CI/CD and supply-chain design | 15 |
| Kubernetes topology and networking | 15 |
| Argo CD and GitOps multi-tenancy | 15 |
| Identity, secrets and security controls | 10 |
| SLO observability and release governance | 10 |
| Data recovery and DR design | 10 |
| FinOps, ADRs and review evidence | 10 |
| **Total** | **100** |

**Pass criteria:** 90/100 or above, with mandatory approval of the threat model, GitOps production write boundary, workload identity and secrets design, data restore/fencing plan, and SLO/RPO/RTO ownership.

## 13. Architecture review package

```text
Project and service owners:
Functional and nonfunctional requirements:
Environments / accounts / regions:
Architecture and trust-boundary diagram:
GitLab permissions / runner isolation:
Repository ownership / promotion policy:
Artifact signing / provenance:
Argo CD AppProjects / cluster permissions:
Workload identity / KMS / secret recovery:
Availability SLO / RPO / RTO:
Capacity and FinOps assumptions:
Threat model and outstanding risks:
Backup / failover / failback plan:
ADRs / approvers / due dates:
Final score / design signoff:
```

## 14. Definition of done and next chapter

The final project blueprint is ready when requirements are traceable to design choices and tests; infrastructure, delivery, secrets, observability and recovery have named owners; critical risks have mitigations; and the review package passes the acceptance gates.

**Next:** Chapter 097 — Enterprise GitOps Final Project: Infrastructure Provisioning, GitLab CI/CD and Argo CD Implementation.
