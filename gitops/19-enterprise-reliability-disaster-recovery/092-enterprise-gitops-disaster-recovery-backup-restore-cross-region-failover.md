# Chapter 092 — Enterprise GitOps Disaster Recovery, Backup, Restore and Cross-Region Failover

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 19:** Enterprise Reliability, Disaster Recovery and Resilience  
**Chapter:** 092 / 100  
**Audience:** SRE, Platform Engineering, DBRE, Security, Incident Command and Release Engineering

> **Safety boundary:** All commands and failure exercises target disposable, explicitly approved lab infrastructure. Never restore over a production namespace, promote a writer, modify live DNS, delete volumes, or disable production reconciliation without a reviewed change and incident authority. Replace placeholders and verify version-specific commands.

## 1. Learning objectives

By the end, you will be able to design a dependency-aware GitOps disaster recovery (DR) plan, define independently measurable RPO/RTO targets, recover Git and immutable artifacts, rebuild Argo CD and Kubernetes safely, restore application-consistent data, enforce single-writer fencing, execute region failover and failback, and produce an auditable DR acceptance report.

## 2. Core distinctions

- **High availability:** handles component or availability-zone faults inside a designed failure domain.
- **Disaster recovery:** restores service when a region, cluster, source-control plane or critical dependency is unavailable.
- **GitOps recovery:** reconstructs desired-state controllers and configuration; it does **not** recreate lost database transactions or automatically restore secrets.
- **RPO:** maximum acceptable data loss, measured between last recoverable committed state and incident boundary.
- **RTO:** maximum acceptable time to restore an agreed service level, measured from declared start to validated business transaction recovery.
- **Control plane vs data plane:** running workloads can remain healthy while Git or Argo CD is unavailable; reconciliation can be healthy while the application is down.

## 3. Reference architecture

```text
             Protected Git + verified DR mirror
                    |         |
            Signed OCI registry + DR replica
                    |         |
             Pinned IaC/bootstrap repository
                    |         |
       +------------+---------+------------+
       | primary region                    | secondary region
       | Kubernetes + Argo CD              | Kubernetes + Argo CD
       | workload identity + KMS           | workload identity + KMS
       | external secret manager           | replicated secrets/DR grants
       | app + primary data writer         | app standby + data replica
       +------------+----------------------+------------+
                    |  fenced writer ownership          |
                    +--- health-gated DNS/traffic ------+
                  Independent monitoring and backup vault
```

Choose **active/passive** for a stateful application unless its database explicitly supports safe multi-writer semantics. Keep the standby's reconciliation scope isolated and prevent two controllers from independently promoting or mutating the same stateful authority. Backup vaults should be independently protected from primary credentials and destructive policies.

## 4. Recovery dependency order

1. Incident declaration, release freeze, authorization and source-of-truth selection.
2. Cloud account access, network, identity, KMS, object-store recovery and infrastructure provisioning.
3. Kubernetes control plane, CNI, CoreDNS, CSI, ingress and admission policy prerequisites.
4. Secret provider, workload identities, Argo CD CRDs, controllers, AppProjects and cluster credentials.
5. Git repositories, image digests, Helm/OCI dependencies and desired-state Applications.
6. Application-consistent persistent data restoration or validated replication promotion.
7. Writer fencing, transactional verification, traffic shift, sustained monitoring and controlled failback.

**Important:** A Git commit, Kubernetes object export, CSI snapshot and native database backup protect different state. Record separate owners, schedules, retention, immutability and restore evidence.

## 5. Recovery policy and planning table

| Recovery asset | Example target (illustrative only) | Recovery evidence |
|---|---|---|
| Git desired state | RPO 15 min; RTO 60 min | Mirror lag and verified commit refs |
| OCI/Helm artifacts | RPO one release; RTO 60 min | Digest, signature and registry pull |
| GitOps controllers | RPO 1 hour; RTO 90 min | Rebuilt Argo CD and healthy reconciliation |
| Stateful application | RPO 5 min; RTO 120 min | Transaction ID/WAL position and synthetic check |
| User-facing routing | RTO 150 min | TLS, DNS and end-to-end client success |

Targets above are **examples, not promises**. Determine each target with business owners, then prove it during drills. The end-to-end RTO is governed by the critical dependency chain, not the fastest component recovery.

## 6. Backup design and operational controls

Maintain protected Git history and independently restorable mirrors; escrow immutable OCI images by digest; version-lock Helm charts and Terraform modules; preserve Argo CD Applications, AppProjects, ApplicationSets and bootstrap definitions; use Velero for supported Kubernetes resources and volume workflows; use CSI snapshots only when supported and pair them with database-native consistency procedures. For PostgreSQL, plan base backup plus WAL/PITR or verified logical restore according to RPO; for MongoDB, follow the operator or backup platform's consistent snapshot/oplog recovery procedure; for Redis, confirm RDB/AOF and durability semantics. Protect encryption keys and recovery identities separately.

**Managed Kubernetes caveat:** EKS, AKS and GKE control-plane/etcd backup access differs from self-managed clusters. Do not assume you can directly restore managed etcd. Recreate managed clusters using IaC and restore supported resources and data through provider-supported workflows.

Backups must be encrypted, access controlled, retention tested, isolated from production deletion authority, monitored for failures, and periodically restored into a clean environment. An untested backup is not a validated recovery path.

## 7. Preflight: isolated staging only

```bash
export LAB_NS=gitops-dr-lab
export RESTORE_NS=gitops-dr-restored
export LAB_FQDN=dr-lab.example.invalid
# Set LAB_REPO_URL and LAB_DATABASE_URL only to disposable test resources.
kubectl config current-context
kubectl cluster-info
kubectl get ns "$LAB_NS" "$RESTORE_NS" --ignore-not-found
velero version --client-only
helm version
git --version
```

Before any restore, confirm destination context, storage class, volume snapshot support, CRD versions, image digests, secret manager availability and approval. **Do not run sample commands against a production context.**

## 8. Hands-on labs — 18 evidence-driven exercises

Each lab requires a ticket, owner, timestamp, approved scope, expected observation, abort threshold and evidence artifact.

### Lab 01 — DR inventory and criticality

**Procedure:** List Git repositories, protected branches, OCI artifacts, Argo CD objects, cluster resources, data stores, DNS, KMS, IdP and owners; classify tier and blast radius.

```bash
kubectl config current-context
kubectl get ns
kubectl -n argocd get applications,applicationsets,appprojects
```

**Pass criteria:** Dependency matrix and named owners. Record command output, observed timing and any deviations. **Abort** if context, data ownership or blast radius differs from the approved plan.

### Lab 02 — RPO/RTO calculation

**Procedure:** Create an approved recovery worksheet for GitOps configuration, service endpoints and each database. Separate maximum tolerable loss from achievable measured loss.

```bash
date -u +%FT%TZ
kubectl -n argocd get applications -o wide
```

**Pass criteria:** Timestamped baseline and signed targets. Record command output, observed timing and any deviations. **Abort** if context, data ownership or blast radius differs from the approved plan.

### Lab 03 — Git repository recovery

**Procedure:** Mirror a disposable repository into a separate protected DR project; compare refs, tags, signed commits and deploy keys. Keep primary read-only during DR rehearsal.

```bash
git clone --mirror "$LAB_REPO_URL" lab-gitops.git
cd lab-gitops.git && git show-ref && git fsck --full
```

**Pass criteria:** Verified mirror, restore credential test. Record command output, observed timing and any deviations. **Abort** if context, data ownership or blast radius differs from the approved plan.

### Lab 04 — Artifact escrow

**Procedure:** Export digest inventory and verify secondary registry availability; require provenance and signature verification before promotion.

```bash
kubectl -n "$LAB_NS" get deployments -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.template.spec.containers[*].image}{"\n"}{end}'
```

**Pass criteria:** Digest manifest and registry recovery evidence. Record command output, observed timing and any deviations. **Abort** if context, data ownership or blast radius differs from the approved plan.

### Lab 05 — Argo CD object export

**Procedure:** Back up non-secret Applications, AppProjects and ApplicationSets for review; secrets require separately governed encrypted backup and tested key recovery.

```bash
kubectl -n argocd get applications.argoproj.io,applicationsets.argoproj.io,appprojects.argoproj.io -o yaml > argocd-objects-review.yaml
```

**Pass criteria:** Sanitized export; no plaintext tokens. Record command output, observed timing and any deviations. **Abort** if context, data ownership or blast radius differs from the approved plan.

### Lab 06 — Bootstrap ordering

**Procedure:** Write a dependency DAG: cloud IAM and network, CNI, CSI, DNS, admission, external secrets, Argo CD, projects, apps, stateful data, traffic.

```bash
kubectl get crd | grep -E 'argoproj|externalsecret|snapshot' || true
```

**Pass criteria:** Dependency-ordered checklist. Record command output, observed timing and any deviations. **Abort** if context, data ownership or blast radius differs from the approved plan.

### Lab 07 — Velero staging backup

**Procedure:** Install approved Velero in isolated lab with scoped object-store credentials; back up only the disposable namespace; check backup phase and errors.

```bash
velero backup create lab092 --include-namespaces "$LAB_NS" --wait
velero backup describe lab092 --details
velero backup logs lab092
```

**Pass criteria:** Completed backup and object-store evidence. Record command output, observed timing and any deviations. **Abort** if context, data ownership or blast radius differs from the approved plan.

### Lab 08 — CSI snapshot readiness

**Procedure:** Verify VolumeSnapshot CRDs, snapshot classes, driver support, retention and consistency contract. Never assume a snapshot equals application-consistent recovery.

```bash
kubectl get volumesnapshotclass
kubectl get csidrivers
kubectl -n "$LAB_NS" get pvc
```

**Pass criteria:** Snapshot capability report. Record command output, observed timing and any deviations. **Abort** if context, data ownership or blast radius differs from the approved plan.

### Lab 09 — Database-consistent restore

**Procedure:** For disposable PostgreSQL, coordinate an approved native base backup plus WAL replay or logical dump; validate transaction boundaries and recovery target.

```bash
pg_dump --format=custom --file=lab092.dump "$LAB_DATABASE_URL"
pg_restore --list lab092.dump | head
```

**Pass criteria:** Validated DB restore into isolated target. Record command output, observed timing and any deviations. **Abort** if context, data ownership or blast radius differs from the approved plan.

### Lab 10 — Secret and key recovery

**Procedure:** Prove DR workload identity can access replicated secret manager and decrypt recovery material without exporting secrets into logs.

```bash
kubectl -n "$LAB_NS" get serviceaccount
kubectl -n "$LAB_NS" get externalsecret
```

**Pass criteria:** Key custody and access evidence. Record command output, observed timing and any deviations. **Abort** if context, data ownership or blast radius differs from the approved plan.

### Lab 11 — Restore into alternate namespace

**Procedure:** Restore namespace-scoped stateless resources to a disposable destination after reviewing resource mappings, CRDs and existing objects.

```bash
velero restore create lab092-restore --from-backup lab092 --namespace-mappings "$LAB_NS:$RESTORE_NS" --wait
velero restore describe lab092-restore --details
```

**Pass criteria:** No collision, clean restore status. Record command output, observed timing and any deviations. **Abort** if context, data ownership or blast radius differs from the approved plan.

### Lab 12 — Cold bootstrap

**Procedure:** Bootstrap a new isolated cluster with pinned Helm chart versions and reviewed manifests; validate AppProjects before enabling automated sync.

```bash
helm version
kubectl get nodes -o wide
kubectl -n argocd get pods
```

**Pass criteria:** Reproducible bootstrap transcript. Record command output, observed timing and any deviations. **Abort** if context, data ownership or blast radius differs from the approved plan.

### Lab 13 — Argo CD sync safety

**Procedure:** Validate source revisions, destinations, pruning and sync windows. Do not allow both regional controllers to reconcile the same mutable writer.

```bash
kubectl -n argocd get applications -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.destination.server}{" "}{.status.sync.status}{"\n"}{end}'
```

**Pass criteria:** Target ownership and source revision proof. Record command output, observed timing and any deviations. **Abort** if context, data ownership or blast radius differs from the approved plan.

### Lab 14 — Region dependency verification

**Procedure:** Check secondary-region DNS, registry, network policy, IdP, secrets, KMS, quotas, API endpoints and data replication lag.

```bash
kubectl get nodes -L topology.kubernetes.io/region
kubectl -n "$LAB_NS" get networkpolicy
```

**Pass criteria:** Secondary region readiness report. Record command output, observed timing and any deviations. **Abort** if context, data ownership or blast radius differs from the approved plan.

### Lab 15 — Writer fencing rehearsal

**Procedure:** With a synthetic DB, revoke old-primary writes and prove fence completion before promoting secondary. Fail closed on unknown primary state.

```bash
kubectl -n "$LAB_NS" get pods -o wide
kubectl -n "$LAB_NS" get svc,endpointslices
```

**Pass criteria:** Fencing audit record; single writer. Record command output, observed timing and any deviations. **Abort** if context, data ownership or blast radius differs from the approved plan.

### Lab 16 — DNS and traffic cutover

**Procedure:** Lower TTL ahead of an approved window; test synthetic clients and connection draining; verify health and propagation, not just DNS record changes.

```bash
dig +short "$LAB_FQDN"
curl -fsS --max-time 5 "https://$LAB_FQDN/health"
```

**Pass criteria:** Client-side traffic and synthetic health evidence. Record command output, observed timing and any deviations. **Abort** if context, data ownership or blast radius differs from the approved plan.

### Lab 17 — Failback and reconciliation

**Procedure:** Re-seed the recovered primary from the authoritative secondary, reconcile Git and image digests, then re-establish a single writer.

```bash
git rev-parse HEAD
kubectl -n argocd get applications -o wide
```

**Pass criteria:** Signed failback plan and parity evidence. Record command output, observed timing and any deviations. **Abort** if context, data ownership or blast radius differs from the approved plan.

### Lab 18 — Full DR game day and acceptance

**Procedure:** Run tabletop plus controlled staging drill, record incident timeline, actual RTO and measured RPO, restore checksums, alert response, owner signoffs.

```bash
date -u +%FT%TZ
kubectl -n "$LAB_NS" get pods,svc -o wide
```

**Pass criteria:** Recovery evidence packet and score. Record command output, observed timing and any deviations. **Abort** if context, data ownership or blast radius differs from the approved plan.

## 9. Failover decision gates

**Gate A — Declare:** service owner and incident commander agree that recovery threshold is reached and primary health is insufficient.  
**Gate B — Recoverability:** mirror revision, signed artifacts, secrets, KMS and data recovery point are independently verified.  
**Gate C — Single writer:** old writer is demonstrably fenced; if fencing cannot be proven, do not promote.  
**Gate D — Promote:** restore/promote exactly once under approved DB procedure; validate data invariants and synthetic write/read.  
**Gate E — Route:** shift traffic only after app and data are healthy, TLS valid and rollback authority understood.  
**Gate F — Stabilize:** maintain incident watch, freeze risky releases, collect lag, error-rate and latency evidence.  
**Gate G — Failback:** resynchronize data in the correct direction; fence current writer before switching back.

## 10. Troubleshooting — 20 operational scenarios

| # | Scenario | Symptom | Containment / verification | Prevention |
|---|---|---|---|---|
| 1 | Git host unreachable | Repository fetch failures | Validate DNS, auth, provider status; use verified DR mirror | Restore primary only after integrity checks |
| 2 | Mirror stale | Unexpected missing commits | Compare refs and signed commit IDs; stop cutover | Set mirror lag alerts |
| 3 | Registry unavailable | ImagePullBackOff | Validate digest exists in secondary registry | Restore original image source after tests |
| 4 | Missing image signature | Admission denial | Quarantine artifact; verify provenance and trust root | Require signature gate |
| 5 | Velero backup partial | PartiallyFailed phase | Inspect item-level errors and permissions | Re-run and test restore |
| 6 | Object store denied | AccessDenied | Check DR role, bucket policy, KMS grants | Least-privilege credential test |
| 7 | CSI snapshot unsupported | No VolumeSnapshotClass | Confirm driver and supported storage path | Use native database backup |
| 8 | Snapshot inconsistent | DB checksum/transaction errors | Use application-aware backup and WAL/binlog | Regular restore verification |
| 9 | KMS key inaccessible | Decrypt failures | Validate DR key grants and key-region policy | Escrow/recovery drills |
| 10 | ExternalSecret stale | Secret not synchronized | Inspect controller conditions and provider connectivity | Identity and replication alerting |
| 11 | Argo CD CRDs missing | No matches for kind | Install compatible CRDs before custom resources | Pin versions |
| 12 | AppProject denied | Application invalid | Restore AppProject and destination policy first | Bootstrap dependency checks |
| 13 | Dual controller ownership | Competing syncs | Suspend secondary/primary reconciliation by approved policy | Single active writer/control owner |
| 14 | DB split brain | Two writable primaries | Stop promotion, fence old writer, reconcile divergence | Fencing automation and drill |
| 15 | Replica lag high | RPO breach risk | Delay promotion or accept explicitly authorized loss | Lag threshold alerts |
| 16 | DNS cache stale | Mixed client routing | Inspect TTL, resolver caching, connection pools | Cutover observation window |
| 17 | Health probe false green | Endpoint healthy but transactions fail | Run write/read synthetic checks | End-to-end acceptance tests |
| 18 | Quota exhausted | Pending pods/volumes | Check cloud quotas, node and storage capacity | Reserved DR capacity |
| 19 | Observability dark | No telemetry in DR | Use independent synthetic checks and logs | Out-of-region monitoring |
| 20 | Failback data drift | Checksums or version mismatch | Stop failback, resynchronize authoritative data | Document reversible failback gates |

## 11. Eight production runbooks

### RB-01 Declare DR

Trigger: approved outage threshold. Incident commander records severity, incident ID, region health, affected SLIs and decision authority. Freeze releases; preserve evidence. Exit: declared recovery strategy or return to primary.

**Required record:** incident/change ID, operator, UTC timestamps, exact commands and approvals, observed state, abort decision, validation screenshots/logs and communication updates.

### RB-02 Recover Git and artifacts

Verify mirror integrity, protected refs, deployment commit and signed OCI digests. Rotate compromised credentials through approved vault. Exit: reproducible immutable desired state. Rollback: stop sync and return to trusted mirror.

**Required record:** incident/change ID, operator, UTC timestamps, exact commands and approvals, observed state, abort decision, validation screenshots/logs and communication updates.

### RB-03 Restore control plane

Provision clean DR cluster using pinned IaC, network, DNS, CSI, policies, identities, secret controller and Argo CD in dependency order. Exit: API and reconciliation checks pass. Rollback: disable sync and preserve cluster forensics.

**Required record:** incident/change ID, operator, UTC timestamps, exact commands and approvals, observed state, abort decision, validation screenshots/logs and communication updates.

### RB-04 Restore persistent data

Confirm backup timestamp, encryption key, native DB recovery and WAL/binlog boundary. Restore to isolated target; run integrity and business invariants. Exit: signed RPO evidence. Rollback: keep target isolated, never overwrite sole good copy.

**Required record:** incident/change ID, operator, UTC timestamps, exact commands and approvals, observed state, abort decision, validation screenshots/logs and communication updates.

### RB-05 Fence and promote writer

Verify old-primary write isolation at network, identity and database layers. Require dual authorization, explicit epoch/lease or equivalent fencing evidence. Promote once, run transactional probes. Abort: uncertain old-writer state.

**Required record:** incident/change ID, operator, UTC timestamps, exact commands and approvals, observed state, abort decision, validation screenshots/logs and communication updates.

### RB-06 Shift user traffic

Check TLS, ingress, WAF, DNS TTL, health and synthetic transactions. Move a small controlled cohort before full cutover where feasible. Monitor error rate and saturation. Rollback only when writer authority and data direction are safe.

**Required record:** incident/change ID, operator, UTC timestamps, exact commands and approvals, observed state, abort decision, validation screenshots/logs and communication updates.

### RB-07 Reconcile and stabilize

Unfreeze approved delivery paths gradually; compare Git revisions, Application sync status, resource health, data lag and error budgets. Keep old region fenced until explicitly released. Exit: sustained SLO observation window.

**Required record:** incident/change ID, operator, UTC timestamps, exact commands and approvals, observed state, abort decision, validation screenshots/logs and communication updates.

### RB-08 Failback and close

Plan reverse replication and resynchronization; take fresh backup; validate parity; schedule change window; fence current writer before reverse promotion. Publish RCA, measured RTO/RPO, owners, remediation deadlines and retest date.

**Required record:** incident/change ID, operator, UTC timestamps, exact commands and approvals, observed state, abort decision, validation screenshots/logs and communication updates.

## 12. Evidence and scorecard (100 points)

| Category | Points | Evidence |
|---|---:|---|
| Recovery objectives and dependency ownership | 15 | Signed RPO/RTO and service inventory |
| Git, registry and immutable supply chain | 10 | Mirror integrity and verified digests |
| Backup and encrypted key recovery | 15 | Successful clean-room restore |
| Kubernetes and Argo CD bootstrap | 15 | Version-pinned rebuild transcript |
| Database consistency and single-writer fencing | 15 | Transaction check and fence proof |
| Cross-region routing and observability | 10 | Client-side synthetic health |
| Failback and rollback readiness | 10 | Reverse-sync and abort plan |
| Game day, incident communication and remediation | 10 | Timed exercise and owner signoff |
| **Total** | **100** | |

**Mandatory gates (regardless of score):** no production blast radius; no plaintext secret exposure; successful application-consistent data recovery; provably single writer; signed RPO/RTO measurements; functioning user-facing transaction; validated failback/rollback ownership. Recommend 90/100 minimum plus all mandatory gates for acceptance.

## 13. Sample DR drill report template

```text
Incident/drill ID:
Primary / secondary region:
Incident commander / database owner / platform owner:
Start UTC / declaration UTC / recovered transaction UTC:
Target RPO / observed RPO:
Target RTO / observed RTO:
Source Git revision / OCI digest:
Backup ID / DB recovery point / validation checksum:
Old writer fence evidence:
DNS/traffic change ID and observed client health:
Alerts and synthetic check results:
Abort decisions / unexpected impacts:
Runbook deviations / corrective actions / owners / due dates:
Approvers / next scheduled restore drill:
```

## 14. Cleanup and rollback

In the lab, first return synthetic traffic to its original endpoint and verify the authoritative writer. Only then delete **explicitly identified disposable** restored namespaces, backups and temporary artifacts according to retention policy. Never delete a backup used as sole recovery evidence. Keep redacted drill logs and checksums in the approved evidence store.

## 15. Definition of done

The team can rebuild a clean isolated GitOps control plane from pinned sources, restore representative stateful data to a known point, demonstrate verified old-writer fencing, execute client-observed regional cutover, safely reverse the operation, and show measured RPO/RTO within approved limits. Publish the dependency map, drill artifacts, exception register and follow-up owners.

**Next:** Chapter 093 — Enterprise GitOps Business Continuity, Chaos Engineering and Disaster Recovery Game Days.
