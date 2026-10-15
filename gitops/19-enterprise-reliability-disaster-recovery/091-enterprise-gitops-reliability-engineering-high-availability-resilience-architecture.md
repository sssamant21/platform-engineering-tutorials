# Chapter 091 — Enterprise GitOps Reliability Engineering, High Availability and Resilience Architecture

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 19:** Enterprise Reliability, Disaster Recovery and Resilience  
**Chapter:** 091 / 100  
**Audience:** SRE, Platform Engineering, DBRE, Release Engineering and Incident Response

> **Safety:** Execute experiments only in approved isolated staging environments. Validate context, blast radius, rollback owner, and abort criteria before changes.

## 1. Objectives

Distinguish application availability, delivery availability, reconciliation latency, and recovery readiness. Define SLOs for each and assign owners.

## 2. Failure domains

Inventory Git provider, GitLab runners, OCI registry, DNS, identity provider, secret manager, Argo CD components, Kubernetes API, network, storage and cloud region. Document independent and correlated failures.

## 3. Reference architecture

Use multi-AZ Kubernetes nodes, redundant Argo CD server/repo-server/application-controller capacity where supported, external HA Redis as appropriate, disruption budgets, topology spread, protected Git and registry, and independent monitoring. HA within a region is not disaster recovery.

## 4. Sizing and quorum

Size application-controller sharding against observed reconciliation load. Verify Redis HA behavior and repository-server cache characteristics. Keep etcd quorum managed by provider; never assume increasing replicas guarantees availability.

## 5. Recovery objectives

Define RTO and RPO separately for stateless application delivery, GitOps configuration, Kubernetes state, and persistent data. Back up Git repository, cluster bootstrap material, credentials recovery procedures and stateful data independently.

## 6. GitOps bootstrap

Maintain a tested break-glass bootstrap path with pinned tool versions and approved identity. Restore cluster prerequisites, CNI, storage, ingress, secret delivery and Argo CD before restoring Applications.

## 7. Safety

Run all fault injections only in isolated staging. Do not delete live volumes, rotate production credentials, or simulate regional failure on active traffic. Require explicit fencing before promoting a stateful writer.

## 8. Lab 1 — Baseline

Verify context and environment: `kubectl config current-context`; `kubectl -n argocd get deploy,sts,pdb,pods -o wide`; `kubectl -n argocd get applications.argoproj.io -o wide`. Record Git revision, cluster and service health.

## 9. Lab 2 — Replica placement

Inspect topology and replica spread with `kubectl -n argocd get pods -o wide` and `kubectl get nodes -L topology.kubernetes.io/zone`. Compare pod placement against failure-domain policy.

## 10. Lab 3 — Disruption budgets

Use `kubectl -n argocd get pdb -o yaml`; verify `disruptionsAllowed` and ensure voluntary disruptions cannot remove all serving replicas. Document limitations for involuntary failures.

## 11. Lab 4 — Repository outage

In staging, block a synthetic Git source or use an isolated mock endpoint. Verify already-running applications continue serving; measure reconciliation staleness and alerting. Restore access and confirm desired revision.

## 12. Lab 5 — Registry outage

Block a disposable image registry for a staging deployment. Observe image-pull failures and recovery after restoring access. Never assume cached images exist on replacement nodes.

## 13. Lab 6 — Identity outage

Use a staging identity mock to simulate failed SSO and token refresh. Verify break-glass access is controlled, audited and expires after the exercise.

## 14. Lab 7 — Controller failure

On an isolated Argo CD installation, disrupt one controller replica using approved tooling. Observe leadership/sharding, queue growth and reconciliation recovery. Abort on unexpected scope.

## 15. Lab 8 — Repo-server failure

Disrupt one staging repo-server pod after confirming redundancy. Measure manifest generation failures, queue depth and recovery. Capture evidence of source freshness.

## 16. Lab 9 — Node and AZ loss

Use disposable nodes or a simulator to model an AZ failure. Verify scheduling, topology spread, service endpoints and data dependency behavior without impacting production.

## 17. Lab 10 — Restore from Git

Bootstrap an empty staging cluster from an approved Git revision. Validate policy, namespaces, workload identities, secret delivery, applications and user-facing synthetic checks.

## 18. Lab 11 — Stateful fencing

Simulate primary failure using a disposable database with synthetic data. Prove old-writer fencing, consistency validation and documented rollback before any promotion.

## 19. Lab 12 — Telemetry failure

Temporarily disable a synthetic telemetry exporter, not production monitoring. Verify no-data alerts and independent local checks. Ensure release gates fail closed.

## 20. Lab 13 — Regional recovery

In a sandbox, rebuild an application in a secondary region using immutable artifacts and approved Git. Measure recovery duration, DNS/traffic-switch readiness and dependencies.

## 21. Lab 14 — CI runner loss

Stop a disposable GitLab runner and validate queued jobs, fallback runner eligibility, protected variable controls and retry idempotency.

## 22. Lab 15 — Capacity pressure

Generate bounded synthetic reconciliation and manifest workload. Measure controller queue depth, API throttling, repo-server latency and resource saturation.

## 23. Lab 16 — Backup validation

Restore representative bootstrap configuration and synthetic state into a separate namespace or cluster. Record restore checksum and evidence; backup success alone does not prove recovery.

## 24. Lab 17 — Resilience game day

Run a tabletop and controlled multi-fault staging scenario. Record incident commander, timeline, abort criteria, recovery decisions and SLO impact.

## 25. Lab 18 — Acceptance

Repeat critical recovery paths from a clean environment, capture timestamps, sign off RTO/RPO evidence and document corrective actions.

## 26. Troubleshooting matrix

Cases: controller crash loops; repo-server OOM; Redis unavailable; Git authentication failure; Git rate limit; registry outage; DNS outage; API throttling; admission webhook timeout; node eviction; AZ loss; lost secrets; expired certificates; stale ApplicationSet targets; reconciliation backlog; SSO outage; telemetry blind spot; split-brain risk; incomplete restore; failed regional cutover. For each, capture symptoms, signals, containment, verified fix and prevention.

## 27. Production runbooks

RB-01 Argo CD component degradation; RB-02 Git source outage; RB-03 registry outage; RB-04 cluster control-plane impairment; RB-05 AZ failure; RB-06 bootstrap restoration; RB-07 stateful failover and fencing; RB-08 region recovery. Each requires trigger, owner, preflight, decision gate, execution, validation, rollback and communications.

## 28. Acceptance scorecard

Architecture and ownership 15; HA and placement 15; dependency resilience 15; recovery objectives 10; bootstrap and backup restore 15; stateful safety 10; observability 10; game-day evidence 10. Total 100. Mandatory gates: no unapproved blast radius, old-writer fenced, successful restore, verified synthetic availability, and recorded recovery times.

## 29. Definition of done

Publish architecture diagram, component inventory, dependency graph, lab evidence, alerting and recovery metrics, signed acceptance report, and corrective action register. Treat examples as environment-specific templates; verify actual Argo CD version and provider support.
