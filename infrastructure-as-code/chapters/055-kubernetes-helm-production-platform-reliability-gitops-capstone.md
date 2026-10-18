# Chapter 055 — Kubernetes and Helm Production Platform Engineering, Reliability and GitOps Capstone

**Part 11 — Kubernetes and Helm | Chapter 055/120 — Part 11 final capstone**  
**Audience:** Platform engineering, SRE, DBRE, security and change-management teams.  
**Prerequisites:** Chapters 051–054, Terraform >=1.7, Python >=3.9. Optional live integration requires an approved disposable Kubernetes cluster, Helm and cloud/cluster access.

> **Evidence boundary:** The mandatory Terraform root contains only \`terraform_data\` contracts and creates **no cloud, Kubernetes, Helm, PVC or database resources**. The policy gate validates declared evidence and simplified plan fixtures, not native Terraform plans, actual Kubernetes controls or live recovery. Review-only manifests are not deployable production infrastructure. Never perform a stateful Helm uninstall, namespace/PVC deletion or forced database failover without authorized DBRE approval.

## 1. Capstone mission and learning outcomes

Build a production-ready **operating model** for Kubernetes platform provisioning and application delivery: cloud cluster infrastructure, namespace and identity governance, Helm add-ons, GitOps applications, stateful services, observability, change safety, disaster recovery and FinOps. The learner must produce a threat model, dependency architecture, validated Terraform contract, negative tests, operational runbooks, game-day evidence and a 100-point final acceptance report.

The fictional workload is a patient-facing API backed by PostgreSQL and Redis. It uses an ingress controller, metrics stack and a database operator; availability and consistency are essential. Target SLO **99.9% monthly availability**, latency p95 <=300 ms, **design-target** RPO <=15 minutes and RTO <=60 minutes. These are assessment goals, not achieved measurements.

## 2. Enterprise architecture

~~~text
                     Change request + pull request
                                 |
                   CI: fmt / test / plan / policy
                                 |
                      OIDC short-lived identity
                                 |
                 Remote encrypted, locked TF state
                    /            |             \
            Cluster root     Tenant root     Add-on root
           EKS/AKS/GKE      NS/RBAC/PSA       Helm/CSI/DNS
             nodes/CNI      quotas/netpol     monitoring
                    \            |             /
                       GitOps handoff boundary
                                |
                       Argo CD or Flux
                                |
              API Deployment -- Service -- Ingress
                 |                 |
               HPA/PDB          network policy
                 |
            PostgreSQL operator + PVC + WAL/PITR
                 |
         isolated backup/restore validation
                 |
           Prometheus / OpenTelemetry / logs
                 |
          SLO + incident command + FinOps
~~~

**Dependency sequence:** cloud identity/network and cluster -> CNI/CSI/DNS -> namespace/PSA/RBAC/quota/network policy -> CRDs/operators -> workload delivery -> probes/PDB/HPA -> observability and backup verification -> operational acceptance. Separate applies are necessary when a provider must discover a newly installed CRD schema.

## 3. Ownership and reconciliation boundaries

| Layer | Source of truth | Control |
|---|---|---|
| Cloud networking and managed cluster | Terraform cloud root | approved plan and drift |
| Platform tenant governance | Terraform Kubernetes root | RBAC, quotas, PSA, NetworkPolicy |
| Shared Helm infrastructure add-ons | Terraform **or** GitOps, choose one | chart pin, provenance, lifecycle |
| Application Deployments and charts | Argo CD / Flux | Git reconciliation, health |
| HPA replica counts | Kubernetes HPA | field ownership |
| Database operator and data | approved operator + DBRE | backup, quorum, restore |
| Secrets | workload identity + secret manager | rotation, no plaintext TF state |

Do not assign Terraform and Argo CD/Flux to the same Helm release or rendered resources. Document every controller's resource and field ownership. A Helm rollback does not reverse external SQL schema migrations or recover deleted persistent data.

## 4. Security and reliability baseline

- **Identity:** short-lived CI OIDC, dedicated Kubernetes ServiceAccounts, namespace-scoped RBAC, no wildcard ClusterRoleBindings, API access only when needed.
- **Admission:** Pod Security Admission restricted where supported, signed/pinned images, reviewed chart hooks and CRDs; least privilege for controllers.
- **Network:** CNI-enforced default-deny ingress/egress, explicit DNS and database traffic, TLS/mTLS as appropriate, controlled ingress and egress.
- **Capacity:** resource requests/limits, ResourceQuota/LimitRange, PDB, topology spread, node autoscaler and HPA pool-budget calculations.
- **Storage:** CSI StorageClass, reclaim policy, zone-aware PVC placement, encryption, snapshots plus database-aware WAL/PITR, tested restore.
- **Delivery:** immutable image digests, Helm chart provenance/version, staged CRDs, progressive rollout, health checks and compatible rollback.
- **Observability:** golden signals, kube-state-metrics, audit logs, traces, storage alerts, error budgets and deployment annotations.
- **Cost:** cluster/node rightsizing, PV orphan detection, ingress egress, observability retention and namespace chargeback.

## 5. Reliability math and acceptance thresholds

**Availability error budget:** 99.9% monthly availability allows approximately 43.2 minutes of downtime over a 30-day month (0.001 × 30 × 24 × 60). This is a target budget; do not equate it to measured availability.

**Database connection budget:** If 12 API pods each allow 40 connections, peak pool demand is 480, excluding jobs, migrations and monitoring. If the database safe application budget is 300, cap pools or scale replicas before rollout. Include PgBouncer/connection proxy behavior in capacity tests.

**Disruption budget:** A 3-replica stateless Deployment with \`minAvailable: 2\` permits at most one voluntary disruption when all replicas are healthy. For a quorum database, PDB settings do not replace leader/quorum safeguards.

**Recovery evidence:** Record actual latest recoverable transaction, backup age, WAL continuity, restore start/end, data checksums and client cutover. A CSI snapshot alone may not be transaction-consistent.

## 6. Capstone executable lab sequence

Root: \`infrastructure-as-code/labs/chapter-055/\`.

### Lab 1 — Offline Terraform enterprise contracts

~~~bash
cd infrastructure-as-code/labs/chapter-055
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=dev.tfplan
terraform apply dev.tfplan
terraform output -json
terraform state list
terraform destroy -var-file=environments/dev.tfvars
~~~

The four \`terraform_data\` contracts cover platform foundation, tenant/security, delivery/Helm/GitOps and operations/DBRE. Production preconditions reject missing backups, dual ownership, broad RBAC, unapproved PVC deletion, untested restore, missing policy enforcement and absent approvals. They are declared assertions only; no cluster resources are created.

### Lab 2 — Policy-as-code and adversarial fixtures

~~~bash
python3 capstone_gate.py fixtures/capstone-safe.json fixtures/plan-safe.json capstone-policy.json
python3 capstone_gate.py fixtures/capstone-unsafe.json fixtures/plan-destructive.json capstone-policy.json
python3 -m unittest -v test_capstone_gate.py
bash run-preflight.sh
~~~

The safe fixture must pass; unsafe/destructive fixtures must exit nonzero. The simplified plan fixture rejects delete/replace and unapproved types. For real production CI, write a separate, tested adapter for \`terraform show -json\`, provider-specific schemas, unknowns and drift, then validate effective Kubernetes admission and network enforcement.

### Lab 3 — Optional approved sandbox integration

1. **Change gate:** confirm approved cluster context, identity, namespace, cost budget, ticket, backup and rollback.
2. **Cluster and tenant:** validate CNI/CSI, DNS, RBAC impersonation, PSA restricted, quotas, default-deny and scoped DNS/DB connectivity.
3. **Helm add-ons:** pin provider/chart/images, render and review manifests, install non-stateful test add-on, validate release health and rollback.
4. **GitOps handoff:** deploy test API using Argo CD or Flux, prove Terraform does not reconcile its objects, then intentionally introduce drift and verify recovery.
5. **Availability:** verify readiness/startup/liveness, PDB, topology spread, HPA and load-test p95 latency.
6. **Stateful safety:** deploy an approved **disposable** database/operator, perform database-consistent backup with WAL, restore to isolated namespace, measure RPO/RTO.
7. **Observability:** record SLO, error budget, pod restarts, saturation, database connections, PV utilization and cost.
8. **Cleanup:** delete only disposable resources after confirming no retained data, backups or shared infrastructure are affected.

### Lab 4 — Production incident game day

Inject a failing Helm hook, missing CRD, bad network egress, exhausted namespace quota, unavailable zone, Pending PVC, stuck PDB drain, GitOps/Terraform ownership collision, HPA-driven DB connection exhaustion and a corrupted database requiring point-in-time restore. For each, record detection, impact, owner, hypothesis, containment, rollback/restore, validation, timestamps and preventive action.

## 7. SRE/DBRE incident response matrix

| Failure | Detection | First diagnostics | Recovery gate |
|---|---|---|---|
| API 5xx after chart upgrade | ingress error rate | Helm history, pods, probes | compatible rollback and SLO |
| CRD/operator upgrade mismatch | admission failures | CRD served/storage versions | stage compatible migration |
| GitOps/Terraform oscillation | perpetual drift | owner registry, managed fields | pause one controller |
| DNS blocked by NetworkPolicy | name resolution timeout | CNI, UDP/TCP 53 | narrow DNS egress |
| PostgreSQL connection storm | max connections | HPA replicas × pools | cap fan-out, backpressure |
| StatefulSet/PVC Pending | unschedulable | CSI, zone, StorageClass | preserve PV, fix topology |
| Node drain blocked by PDB | eviction denied | quorum, ready replicas | restore health before drain |
| Leaked Secret in Terraform state | security alert | state/Helm values audit | revoke and rotate |
| Namespace/PVC delete planned | plan delete/replace | ownership, reclaim policy | deny, obtain DBRE approval |
| Regional outage | loss of service | backup/WAL, secondary readiness | isolated restore/cutover |
| Cost spike | cloud billing anomaly | idle nodes/PVs/egress | safe rightsize with SLO check |
| Telemetry gap | missing alerts/traces | agents, exporters, RBAC | restore visibility before rollout |

## 8. Troubleshooting commands

~~~bash
kubectl config current-context
kubectl get nodes -o wide
kubectl get ns --show-labels
kubectl get deploy,sts,ds,job,cronjob,pods,pdb,hpa -A
kubectl get networkpolicy,resourcequota,limitrange -A
kubectl get pvc,pv,storageclass
kubectl get events -A --sort-by=.lastTimestamp
kubectl auth can-i get secrets -n NAMESPACE
helm list -A
helm status RELEASE -n NAMESPACE
helm history RELEASE -n NAMESPACE
terraform providers
terraform state list
terraform plan -var-file=environments/dev.tfvars
~~~

Do not paste kubeconfig tokens, Secret payloads, Helm values containing credentials or Terraform state contents into tickets.

## 9. Production runbooks

**R1 — Preflight and maintenance:** check exact cluster context, state lock, approved plan, identity, owner, chart pins, RBAC, admission, CNI, CSI, PDB, DB backup, rollback, SLO budget, ticket and DBRE/Security approval. Deny delete/replace.

**R2 — Deployment/Helm failure:** freeze further rollouts, inspect hooks, release history, pod events and readiness, restore compatible chart/image, validate API and database compatibility.

**R3 — GitOps drift:** determine controller ownership, pause the competing reconciler under approval, reconcile Git and Terraform state, verify only one owner remains.

**R4 — Database connection exhaustion:** measure HPA × pool capacity, reduce retry amplification, cap pools, enable backpressure and validate transaction latency/success.

**R5 — CSI/PVC/StatefulSet incident:** preserve PV/PVC, inspect zone/attachment, operator quorum and backup; coordinate DBRE before detach, migration, snapshot or restore.

**R6 — Security exposure:** revoke exposed identities, audit Terraform state/Helm metadata and Kubernetes API, rotate secrets, validate effective RBAC and egress controls.

**R7 — Disaster recovery:** freeze unsafe writes, choose last consistent backup/WAL, restore isolated environment, validate data and client compatibility, cut over, measure actual RPO/RTO.

**R8 — Postmortem and readiness:** preserve sanitized evidence, error budget, audit trail, runbook changes, owner approvals and prevention actions.

## 10. 100-point final capstone assessment

| Domain | Points | Required proof |
|---|---:|---|
| Architecture, dependency staging and ownership | 15 | design, state isolation and handoff |
| Identity, RBAC, network policy and admission | 15 | effective permissions and flow tests |
| Helm, GitOps, CRDs and progressive delivery | 15 | chart audit, rollout and rollback |
| Stateful storage, database backups and DR | 20 | isolated consistent restore, RPO/RTO |
| Terraform contracts, policy and negative tests | 15 | executed CI and plan evidence |
| SRE game day, SLO and incident runbooks | 15 | timeline, telemetry and recovery |
| FinOps, change approvals and documentation | 5 | cost, ticket and sign-offs |
| **Total** | **100** | |

**Pass >=85/100 and zero critical failures.** Critical failures: wildcard cluster-admin, unapproved delete/replace, secrets in state, unreviewed privileged chart, competing Terraform/GitOps ownership, absent database restore or unproven RPO/RTO. Publication, code review and authored tests do **not** constitute live operational acceptance.

## 11. Deliverables and exit criteria

Submit: architecture diagram, source-of-truth/ownership table, reviewed Terraform plan, unit-test output, cluster RBAC/CNI/PSA evidence, Helm chart provenance and release history, GitOps handoff proof, SLO/error budget dashboard, DB restore validation with measured RPO/RTO, game-day timeline, 100-point scored acceptance and signed change ticket. Treat any missing live evidence as **pending**, not passed.

**Part 11 (Chapters 051–055) complete upon publication of this chapter; live lab and production acceptance remain separate.**  
**Next:** Chapter 056 — review the master roadmap for the next Part 12 topic and exact title before publishing.
