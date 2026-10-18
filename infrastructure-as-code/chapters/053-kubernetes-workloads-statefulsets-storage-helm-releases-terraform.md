# Chapter 053 — Kubernetes Workloads, StatefulSets, Storage and Helm Releases with Terraform

**Part 11 — Kubernetes and Helm | Chapter 053/120**  
**Audience:** SRE, DBRE, platform engineering, application delivery and security.  
**Prerequisites:** Chapters 051–052; Terraform >=1.7, Python >=3.9; optional approved disposable Kubernetes cluster.

> **Execution boundary:** The mandatory lab uses \`terraform_data\` only: no Kubernetes or Helm provider, cloud credentials, real deployments, databases, PVCs or Secrets. The separate provider examples are review-only. The Python gate checks declared evidence and simplified plan actions; it does **not** verify actual cluster security, real Helm plan semantics or a backup restore. Never run destructive Helm uninstall, StatefulSet or PVC operations against production without DBRE approval.

## 1. Outcomes and production case

Provision and operate Kubernetes Deployments, DaemonSets, Jobs, CronJobs, StatefulSets, Services, ConfigMaps, persistent storage and Helm releases with Terraform while preserving cluster safety, GitOps ownership, application availability and data durability. Model rollouts, scheduling, health probes, PodDisruptionBudgets (PDBs), autoscaling, CSI storage, snapshots, backup, Helm dependencies, chart provenance and rollback.

**Case:** An API Deployment calls PostgreSQL operated by an approved database operator on GKE/EKS/AKS. Prometheus and ingress controllers are installed via pinned Helm charts. A maintenance window must upgrade the application without exceeding its error budget or losing database writes. Recovery objective examples (RPO <=15 min, RTO <=60 min) are design targets, not demonstrated results.

## 2. Reference architecture

~~~text
 Git PR / CI / OIDC  ->  Terraform policy and plan
                             |
          Cloud cluster root (EKS / AKS / GKE)
                             |
            Separate Kubernetes/Helm root
              /              |             \
       Namespace/RBAC     Helm addons     Workload specs
         quotas/PSA       ingress/CSI     Deployment/Job
              |              |             |
        NetworkPolicy      CRDs first    Service + PDB + HPA
                             |             |
                         StorageClass    StatefulSet/operator
                             |             |
                       CSI snapshots    PVC + WAL backup
                             \             /
                           Metrics / logs / traces
                                   |
                            SRE/DBRE restore drill
~~~

**Ownership rule:** Terraform, Helm, Argo CD/Flux and Kubernetes controllers must not concurrently own the same resource or field without a documented boundary. Prefer separate cluster, platform add-on and app roots; bootstrap CRDs before custom resources; verify admission and cluster readiness before deploying workloads.

## 3. Kubernetes workload primitives

| Kind | Desired behavior | Operations caution |
|---|---|---|
| Deployment | stateless replicas, rolling updates | readiness, surge/unavailable, HPA field ownership |
| StatefulSet | stable pod identity, ordinal, volume claim templates | not a replication, failover or backup system |
| DaemonSet | one pod per eligible node | taints, tolerations, privileged agents |
| Job | run to completion | retries, idempotency, backoff, deadlines |
| CronJob | scheduled Jobs | concurrency policy, missed schedules, time zone |
| Service | stable virtual endpoint | endpoints, DNS, network policy, selectors |
| PDB | limit voluntary disruptions | does not protect from involuntary failures |
| HPA | adjust replicas from metrics | database connection fan-out and capacity |
| Helm release | package/versioned deployment | hooks, CRDs, drift and uninstall hazards |

**Probes:** Startup delays liveness/readiness until initialization completes. Readiness controls traffic eligibility; liveness restarts unhealthy containers. A liveness probe checking a downstream database can amplify a database outage into a restart storm. Tune termination grace and graceful shutdown to drain connections.

**Availability:** Use topology spread constraints, node affinity, requests/limits, disruption budgets and rollout strategy. PDBs can block voluntary drains when replicas are unhealthy; do not force eviction of quorum-bearing database pods without an operator-approved procedure.

## 4. StatefulSets and database reliability

StatefulSets provide stable DNS identities and persistent claims, not synchronous replication or automatic backups. For PostgreSQL, MongoDB, Kafka, Redis and Elasticsearch, prefer vetted operators and documented data consistency semantics. Consider:
- Replica quorum, leader election and fencing; zone failure and split-brain risks.
- PVC reclaim policy (\`Delete\` vs \`Retain\`), dynamic provisioning, StorageClass expansion and topology.
- CSI driver and snapshot-controller prerequisites; \`VolumeSnapshotClass\` and snapshot deletion policy.
- Transaction-consistent backups (e.g. PostgreSQL WAL plus base backup), tested restore, encryption and retention.
- Database connection pools during Deployment HPA surges; backpressure, retries and failover.
- Snapshot restore in an isolated namespace/cluster before cutover; test RPO/RTO with application writes.

**Important:** \`WaitForFirstConsumer\` helps bind zonal volumes after scheduling, but does not make a volume multi-zone. A CSI snapshot may not be application-consistent without database-aware coordination.

## 5. Helm provider lifecycle and supply-chain controls

Pin \`hashicorp/helm\`, chart repository, chart version and container image digests. Inspect values, CRDs, hooks, permissions and service accounts. Helm chart upgrades can change resources in place, and Helm rollback does not undo external database migrations or lost data. Use atomic upgrades and timeouts where appropriate; test \`cleanup_on_fail\` and \`wait\` behavior against the pinned provider version. Do not assume every chart supports \`rollback\` the same way.

**Secret handling:** Helm values and Terraform state can contain sensitive values even when marked sensitive in output. Do not put database passwords, TLS private keys or Secret payloads in Terraform state. Prefer External Secrets/CSI Secrets Store or approved secret injection with workload identity. Audit chart templates for ClusterRoleBindings, hostPath, privileged pods and broad network permissions.

**CRD ordering:** Installing a CRD and immediately planning \`kubernetes_manifest\` resources depending on that CRD in the same initial plan may fail API discovery. Split CRD installation and CR creation into separate applies/stages, with readiness checks.

## 6. Terraform root and state architecture

~~~text
iac/
  cluster/              # cloud cluster, network, IAM
  platform-addons/      # CSI, CNI, DNS, ingress, cert-manager
  tenant-policy/        # namespace, RBAC, quota, PSA, NetworkPolicy
  app-workloads/        # Deployments, Services, Jobs, HPA, PDB
  data-operators/       # vetted DB operator, CRDs and backups
  dr-validation/        # isolated restore and SLO evidence
~~~

Use explicit kubeconfig context and short-lived identity. Do not bootstrap a new cluster and initialize the Kubernetes provider from unknown cluster outputs in the same initial plan. Keep state encrypted, locked and segregated by environment. Review \`terraform plan\` delete/replace actions independently of \`prevent_destroy\` (which can be removed with configuration changes). Import existing resources under a documented ownership transfer, not an accidental double-controller takeover.

## 7. Executable labs

Files: \`infrastructure-as-code/labs/chapter-053/\`.

### Lab A — Offline Terraform workload, storage, Helm and operations contracts

~~~bash
cd infrastructure-as-code/labs/chapter-053
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

Four \`terraform_data\` resources enforce declared production controls: workload readiness/PDB/probes, stateful backup/CSI topology, Helm chart pinning and ownership, and operational change/DR approvals. **No cluster resources are created.**

### Lab B — Fail-closed policy and adversarial plan fixtures

~~~bash
python3 workload_gate.py fixtures/workload-safe.json fixtures/plan-safe.json workload-policy.json
python3 workload_gate.py fixtures/workload-unsafe.json fixtures/plan-destructive.json workload-policy.json
python3 -m unittest -v test_workload_gate.py
bash run-preflight.sh
~~~

Safe fixture should pass; unsafe and destructive fixture should exit nonzero. The gate rejects missing evidence, unknown resource types, and simplified \`delete\`/replace actions. **It does not parse native \`terraform show -json\`**; a production pipeline needs a tested provider-aware adapter plus cluster integration tests.

### Lab C — Review-only Kubernetes and Helm example

1. Review \`examples/kubernetes-helm.tf.example\` in a separate disposable sandbox root; verify the exact provider/chart schema before using it.
2. Validate approved context, namespace, scoped RBAC, Pod Security Admission and NetworkPolicy.
3. Plan a Deployment with pinned image digest, probes, resources, PDB and Service; validate endpoints, rollout and graceful termination.
4. Deploy a pinned chart with scoped service account, controlled values and security review; inspect Helm release status, hooks, drift and rollback behavior.
5. For a database operator, stage CRDs before custom resources; create disposable data, perform consistent backup and restore in isolation.
6. Record observed p95 latency, error rate, recovery point, recovery time, PVC reclaim policy and owner sign-offs. Clean up only after verifying no persistent data loss.

### Lab D — Game day

Inject readiness failures, an overaggressive liveness probe, HPA-induced connection exhaustion, CSI volume zone mismatch, stuck Helm release, CRD discovery error, PV deletion, failed snapshot restore and conflicting GitOps reconciliation. Freeze writes and/or deployments as needed; run recovery and record RPO/RTO and error budget impact.

## 8. Production SRE/DBRE troubleshooting matrix

| Incident | Signals | Triage | Safe remediation |
|---|---|---|---|
| Rollout stalls | unavailable replicas, 5xx | \`kubectl rollout status\`, events, probes | fix readiness, rollback |
| CrashLoopBackOff | restart spikes | logs, OOMKilled, liveness | correct probe, resources |
| HPA overwhelms database | too many connections | pods × pool, DB max connections | cap pools, backpressure |
| StatefulSet pod Pending | PVC Pending | CSI, topology, StorageClass | align zone/capacity |
| Volume attach conflict | Multi-Attach errors | PV affinity, old pod attachment | coordinate detach safely |
| Snapshot unusable | restore fails | CSI and WAL consistency | database-aware restore |
| PDB blocks drain | cannot evict | healthy replicas and quorum | restore availability first |
| Helm upgrade stuck | pending-upgrade | hooks, chart diff, API events | controlled release recovery |
| Helm CRD missing | no matches for kind | CRD API discovery | stage CRD installation |
| Terraform/Helm/GitOps drift | perpetual plan diffs | resource ownership | handoff and reconcile |
| PVC deletion planned | delete/replace | state and reclaim policy | block, preserve data |
| Secret in Helm values | state exposure | state access, values audit | revoke/rotate and migrate |

## 9. Diagnostic commands

~~~bash
kubectl config current-context
kubectl get deploy,sts,ds,job,cronjob,pods,pdb,hpa -A
kubectl get pvc,pv,storageclass -A
kubectl get volumesnapshot,volumesnapshotclass -A
kubectl get events -A --sort-by=.lastTimestamp
kubectl describe pod POD -n NAMESPACE
kubectl rollout status deploy/APP -n NAMESPACE
kubectl rollout history deploy/APP -n NAMESPACE
kubectl logs deploy/APP -n NAMESPACE --previous
helm list -A
helm status RELEASE -n NAMESPACE
helm history RELEASE -n NAMESPACE
terraform providers
terraform state list
~~~

Snapshot CRDs and commands may be unavailable unless the CSI snapshot controller is installed. Never dump Kubernetes Secret values, kubeconfig tokens, database credentials or sensitive Terraform state into tickets.

## 10. Production runbooks

**Pre-change:** verify cluster/context, chart and provider pins, image digests, RBAC, quota, PDB, probes, state backup, DBRE restore point, maintenance ticket and rollback. Deny unexpected StatefulSet/PVC deletion.

**Deployment failure:** inspect rollout, endpoints, events and probes; revert immutable image digest, validate p95 latency and error budget. Do not roll back a schema migration without DBRE compatibility review.

**Database connection storm:** quantify HPA scale × pool size; cap connection fan-out, reduce retry storms, enable backpressure, validate transaction success.

**CSI/PVC incident:** preserve PVC and PV, inspect StorageClass/reclaim policy/topology and snapshot status, restore only under DBRE change control, validate consistency and application access.

**Helm failure:** inspect release history, hooks and CRDs, pause competing GitOps reconciliation if approved, roll back compatible release and revalidate resources; do not uninstall a stateful release blindly.

**Regional or data-loss DR:** freeze unsafe writes, locate last-known-good WAL/backup, restore isolated database, validate integrity, cut over application and measure actual RPO/RTO.

## 11. 100-point operational assessment

| Domain | Points | Required evidence |
|---|---:|---|
| Workload topology, rollout and probes | 20 | rollout test and availability |
| Stateful storage, backups and DBRE recovery | 25 | isolated restore, integrity and RPO/RTO |
| Helm chart, CRD, identity and supply chain | 20 | chart review, release rollback |
| Terraform contracts and negative policy tests | 15 | executed test logs and plan |
| Incident drills, observability and SLOs | 10 | incident timeline and metrics |
| Change, FinOps and security approval | 10 | ticket, cost, sign-off |
| **Total** | **100** | |

**Pass >=85/100 with zero critical failures:** no missing database restore, unapproved PVC deletion, privileged chart, leaked secret, uncontrolled Helm uninstall or missed mandatory RPO/RTO. Publication and authored tests are **not** acceptance evidence.

## 12. Review questions and next chapter

How does StatefulSet identity differ from data replication? Why is a CSI snapshot not always transaction-consistent? When can PDBs block maintenance? Why can Helm rollback fail to reverse database changes? Why must Terraform and GitOps ownership be explicit?

**Next proposed:** Chapter 054 — Kubernetes Helm Provider, Chart Lifecycle, GitOps Integration and Policy Automation with Terraform.
