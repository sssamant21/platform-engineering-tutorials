# Chapter 072 — etcd Backup and Restore

**Track:** Kubernetes Administration · **Part 15 — Backup, Disaster Recovery and Business Continuity**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** Kubernetes administrators, SRE, DBRE, platform and security engineers  
**Prerequisites:** Chapter 071; understanding of control-plane architecture, kubeadm, TLS and storage; Windows PowerShell; approved isolated self-managed Kubernetes recovery lab

## 1. Production incident scenario

A self-managed Kubernetes cluster loses control-plane quorum after a storage failure. The API server cannot reliably process writes, controllers stop reconciling, and the platform team must recover from the latest verified etcd snapshot. The recovery must preserve cluster identity and minimize data loss while avoiding accidental restoration into a live production control plane.

**Mission:** inventory etcd topology, take a consistent authenticated snapshot, verify snapshot integrity, rehearse an isolated restore, validate Kubernetes API recovery, and calculate measured RPO/RTO.

**Managed-cluster boundary:** Amazon EKS and Azure AKS operate their managed control-plane etcd. Customers generally cannot run `etcdctl snapshot save` against that managed etcd or directly restore it. Use provider-supported cluster recovery, GitOps/IaC, workload/PVC backups and service-specific data recovery instead. This chapter's direct etcd procedures apply to authorized self-managed clusters.

### Learning objectives

1. Explain etcd's role as Kubernetes' consistent control-plane key-value store.
2. Distinguish etcd quorum, replication, snapshots, WAL and disaster recovery.
3. Locate etcd endpoints, TLS certificates and data directories in self-managed deployments.
4. Capture and verify snapshots using compatible `etcdctl` and `etcdutl` tooling.
5. Plan a **new logical cluster** restore rather than mixing restored and live members.
6. Understand revision bump and compaction marking for Kubernetes watch clients.
7. Validate API availability, controllers, node readiness and application dependencies.
8. Implement secure off-host storage, retention, encryption and restore drills.

## 2. What an etcd backup does—and does not—protect

etcd stores Kubernetes API state, including Deployments, StatefulSets, Secrets, ConfigMaps, RBAC, CRDs and cluster metadata. A snapshot preserves the key-value state at a particular revision.

It does **not** inherently back up:
- Persistent volume contents or CSI snapshots.
- Container images and external registries.
- Cloud load balancers, IAM, VPC/VNet or DNS configuration.
- External database content and Kafka messages.
- Local node files, container runtime state or kubelet configuration.
- Encryption-at-rest keys that may be needed to decrypt stored Kubernetes Secrets.

A Kubernetes API resource snapshot is also not equivalent to an application-consistent database backup. Use the layered approach from Chapter 071.

## 3. etcd topology, quorum and recovery decisions

```text
                  Kubernetes API servers
                     |      |      |
                  etcd member cluster
                     A <--> B <--> C
                     |      |      |
                  WAL + backend on each member
                           |
                   verified snapshot
                           |
                  isolated restore target
```

For a cluster with `n` voting members, quorum is `floor(n/2)+1`. A three-member cluster tolerates one voting-member failure; a five-member cluster tolerates two. Adding a fourth voting member does not increase tolerated failures compared with three.

### Decision tree

| Condition | Preferred approach |
|---|---|
| One member failed; quorum healthy | Replace/repair the failed member using documented member-replacement procedure |
| Temporary connectivity issue | Diagnose network/TLS and restore quorum without overwriting data |
| Quorum irrecoverably lost | Approved disaster-recovery procedure from verified snapshot |
| Snapshot integrity unknown | Verify before any restore attempt |
| Managed EKS/AKS control plane | Provider-supported recovery; no direct etcd manipulation |
| External etcd topology | Follow external-etcd ownership, certificates and membership plan |

**Never use snapshot restore as the first response to an ordinary unhealthy member.** It can discard newer state and require a coordinated control-plane recovery.

## 4. Lab 1 — Establish authority and topology (read-only)

```powershell
Get-Date -Format o
kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
kubectl -n kube-system get pods -o wide
kubectl get --raw='/readyz?verbose'
```

For kubeadm-managed clusters, etcd commonly runs as a static Pod with a manifest on control-plane hosts, but topology varies. Read the manifest **on an authorized control-plane host**:

```bash
sudo test -f /etc/kubernetes/manifests/etcd.yaml
sudo grep -E -- '--(name|data-dir|listen-client-urls|advertise-client-urls|initial-cluster|cert-file|key-file|trusted-ca-file)' /etc/kubernetes/manifests/etcd.yaml
```

Do not publish private key material or copy certificate keys into tickets.

**Expected:** classify self-managed versus managed, stacked versus external etcd, number of members, endpoints, versions, data directory and recovery owner.

## 5. Lab 2 — Verify etcd health and membership

On an authorized self-managed control-plane host with matching etcd tools and valid TLS material:

```bash
export ETCDCTL_API=3
export ETCDCTL_CACERT=/etc/kubernetes/pki/etcd/ca.crt
export ETCDCTL_CERT=/etc/kubernetes/pki/etcd/healthcheck-client.crt
export ETCDCTL_KEY=/etc/kubernetes/pki/etcd/healthcheck-client.key
export ETCDCTL_ENDPOINTS=https://127.0.0.1:2379

etcdctl --endpoints="$ETCDCTL_ENDPOINTS" endpoint health
etcdctl --endpoints="$ETCDCTL_ENDPOINTS" endpoint status -w table
etcdctl --endpoints="$ETCDCTL_ENDPOINTS" member list -w table
```

Certificate paths and endpoints are **examples for kubeadm stacked etcd**; derive actual values from the manifest. External etcd requires its own approved credentials and endpoint list. A localhost endpoint only queries the local member.

**Expected:** capture member IDs, leadership, term, raft index, database size, health and alarms. Check all known endpoints, not only localhost, when evaluating cluster quorum.

## 6. Lab 3 — Prepare backup safety controls

Before snapshotting:

1. Verify sufficient free space for the snapshot and temporary files.
2. Confirm a dedicated backup destination **outside the etcd data directory**.
3. Ensure encryption, permissions and off-host transfer.
4. Confirm snapshot cadence meets RPO.
5. Identify Kubernetes encryption-at-rest configuration and protected key recovery.
6. Confirm tool version compatibility with the etcd server.
7. Record UTC timestamp, cluster identity, member endpoint and backup owner.

```bash
etcdctl version
etcdutl version
df -h /var/lib/etcd /var/backups
date -u +%Y-%m-%dT%H:%M:%SZ
```

Tooling may be delivered in containers or installed separately. Do not install unapproved binaries on production control-plane hosts.

## 7. Lab 4 — Capture a consistent etcd snapshot

**Read-only with respect to etcd state**, but creates a local backup file. Run only with approved credentials and destination.

```bash
sudo install -d -m 0700 /var/backups/etcd
SNAPSHOT="/var/backups/etcd/etcd-$(date -u +%Y%m%dT%H%M%SZ).db"

etcdctl \
  --endpoints="https://127.0.0.1:2379" \
  --cacert="/etc/kubernetes/pki/etcd/ca.crt" \
  --cert="/etc/kubernetes/pki/etcd/healthcheck-client.crt" \
  --key="/etc/kubernetes/pki/etcd/healthcheck-client.key" \
  snapshot save "$SNAPSHOT"

sudo chmod 0600 "$SNAPSHOT"
sha256sum "$SNAPSHOT"
ls -lh "$SNAPSHOT"
```

The endpoint and certificate paths are kubeadm-style examples; substitute confirmed values. Do not snapshot by copying a live data directory as an alternative to the authenticated snapshot API.

**Expected:** `snapshot save` completes and the resulting file has a recorded hash, location and timestamp.

## 8. Lab 5 — Verify snapshot metadata and recoverability

```bash
etcdutl snapshot status /var/backups/etcd/REPLACE_WITH_SNAPSHOT.db -w table
sha256sum /var/backups/etcd/REPLACE_WITH_SNAPSHOT.db
```

Typical snapshot status includes hash, revision, total keys and size. The hash is a useful integrity signal but does not prove a Kubernetes control plane can successfully recover.

### Evidence worksheet

```text
Snapshot ID/path:
Cluster/environment:
Captured UTC:
etcd server version:
etcdutl version:
Snapshot revision:
Total keys:
Snapshot size:
SHA-256:
Off-host copy:
Encryption/key reference:
Last successful restore drill:
```

**Expected:** snapshot status is readable and checksum is recorded. Do not call a snapshot validated until an isolated restore succeeds.

## 9. Lab 6 — Transfer and protect the backup

A local snapshot on the failed control-plane host may be lost during the incident. Transfer through an approved encrypted channel to protected object storage or backup infrastructure.

### Required controls

- Encrypt in transit and at rest.
- Use dedicated backup writer and separate restore reader permissions.
- Restrict deletion and enforce retention/immutability where available.
- Maintain cross-zone or cross-region copies according to the disaster scenario.
- Protect encryption keys independently from the cluster.
- Verify uploaded object size/hash and restore accessibility.
- Audit access, failed backups and unusual deletions.

**Never include plaintext Secrets, credentials, etcd certificates or snapshot content in a public repository.** An etcd snapshot can contain sensitive Kubernetes Secret data, even when the cluster uses encryption-at-rest mechanisms.

## 10. Lab 7 — Design an isolated restore plan

**High-risk boundary:** restore into a new, isolated data directory and an approved **nonproduction** recovery control plane. Never point a restored member at a live cluster's data directory or reuse live cluster membership without a coordinated disaster-recovery plan.

### Preflight

```text
Recovery cluster ID:
Source snapshot revision:
New etcd member names:
New peer URLs:
New client URLs:
New data directories:
Kubernetes version:
etcd version:
API server configuration:
Encryption-at-rest keys:
Expected RPO/RTO:
Rollback strategy:
Network isolation:
Approver:
```

A restore initializes new member data from snapshot. Restored cluster membership, peer URLs and bootstrap settings must match the recovery topology. For Kubernetes, avoid restoring a stale revision without considering watch-cache invalidation.

## 11. Lab 8 — Restore a snapshot in a disposable single-member lab

**Do not execute on a production control-plane host.** This is an isolated Linux VM/container lab with an approved matching `etcdutl` binary. The example assumes a snapshot already copied to `/tmp/etcd-recovery/snapshot.db`.

```bash
mkdir -p /tmp/etcd-recovery

etcdutl snapshot status /tmp/etcd-recovery/snapshot.db -w table

etcdutl snapshot restore /tmp/etcd-recovery/snapshot.db \
  --name recovery-1 \
  --data-dir /tmp/etcd-recovery/member-1 \
  --initial-cluster recovery-1=http://127.0.0.1:2380 \
  --initial-advertise-peer-urls http://127.0.0.1:2380 \
  --initial-cluster-token ch072-isolated-restore
```

For a Kubernetes recovery rehearsal, use an **appropriately sized revision bump and `--mark-compacted` when supported** so controllers and clients do not continue with stale watches. Choose the bump using the elapsed time and write-rate assumptions; an arbitrary number is not universally safe. Check `etcdutl snapshot restore --help` for the installed version.

A restored data directory is **not yet** a functioning Kubernetes recovery. Starting an isolated etcd process and API server requires matching certificates, URLs, configuration and cluster state. Do not start a second process on live ports.

**Expected:** restore exits successfully and creates a new data directory. Continue with an isolated control-plane startup and verification under a separate approved lab plan.

## 12. Lab 9 — Kubernetes-specific revision and watch safety

Kubernetes controllers, informers and API servers rely on etcd revisions and watches. A restore to an earlier revision can invalidate assumptions held by components that previously observed higher revisions.

### Recovery controls

1. Restore into a new logical etcd cluster with a verified snapshot.
2. Use supported revision bump and compaction marking for Kubernetes restore scenarios.
3. Restart/reconnect API servers and controllers in a controlled sequence.
4. Reconcile API state and detect objects created after the snapshot.
5. Validate that operators and GitOps do not overwrite restored state incorrectly.
6. Check secrets encryption configuration before API startup.

**Expected:** explain why a snapshot restore can appear healthy at the etcd layer yet leave Kubernetes controllers inconsistent if revisions and watch state are mishandled.

## 13. Lab 10 — Validate control-plane and workload recovery

In an **isolated recovered Kubernetes cluster** after an approved startup procedure:

```powershell
kubectl config current-context
kubectl get --raw='/readyz?verbose'
kubectl get nodes -o wide
kubectl get namespaces
kubectl get crds
kubectl get deployments,statefulsets,daemonsets -A
kubectl get pvc -A
kubectl get events -A --sort-by=.lastTimestamp
```

### Acceptance gates

- API readiness and authentication work.
- Controllers reconcile new test objects.
- RBAC, admission, CRDs and operators behave as expected.
- Nodes register and become Ready.
- PVCs and storage drivers are functional.
- External identity, DNS and certificates are available.
- Applications pass health and data-integrity checks.
- Restore timestamps and observed RPO/RTO are recorded.

**Do not route customer traffic to a recovered environment until data integrity, dependency ownership and cutover approval are complete.**

## 14. Lab 11 — RPO/RTO measurement

Assume a verified snapshot at 09:50 UTC, incident at 10:00 UTC, API recovery at 10:35 UTC and customer service recovery at 11:10 UTC.

```text
Potential etcd state loss = 10 minutes
API control-plane recovery = 35 minutes
Customer-facing service recovery = 70 minutes
```

These are illustrative values. Actual RPO depends on the recoverable snapshot revision and any additional data recovery; RTO must include application and dependency restoration, not only etcd startup.

### Measurement worksheet

```text
Incident timestamp:
Last verified recoverable snapshot:
Snapshot revision:
etcd restore started:
etcd quorum healthy:
API server ready:
Controllers healthy:
Application ready:
Customer traffic restored:
Measured etcd state loss:
Measured customer RTO:
Exceptions and data divergence:
```

## 15. Lab 12 — Incident tabletop: quorum lost and stale snapshot

**Scenario:** a three-member etcd cluster loses two members. A snapshot from 45 minutes earlier is verified. One API server still has cached objects, and an automation controller is attempting to reconcile resources against the unavailable API. The business RPO is 15 minutes.

### Tasks

1. Confirm quorum loss and exclude a transient network partition.
2. Determine whether member recovery is possible without snapshot restore.
3. Calculate whether the latest verified snapshot satisfies RPO.
4. Escalate the 30-minute RPO gap to the incident commander and business owner.
5. Protect encryption keys and off-host snapshot copy.
6. Plan isolated restoration with revision/watch safeguards.
7. Freeze conflicting automation until recovery sequencing is approved.
8. Validate API state, workloads, PVCs and external data dependencies.
9. Record customer impact, measured RTO and residual data loss.
10. Produce preventive actions for snapshot frequency and restore drills.

**Expected:** do not silently claim RPO success when the available snapshot is older than the approved objective.

## 16. Troubleshooting matrix

| Symptom | Likely cause | Investigation |
|---|---|---|
| `snapshot save` connection refused | Wrong endpoint, etcd down | Manifest, listener, network |
| TLS handshake/auth failure | Wrong cert/key/CA or SAN | TLS paths and certificate validity |
| `snapshot status` fails | Corrupt/incompatible file | Hash, file copy, tool version |
| Restore fails on existing directory | Data directory already populated | Use clean isolated target |
| Recovered member cannot form cluster | Peer URLs/membership mismatch | Initial cluster configuration |
| etcd healthy but API down | API server TLS/config or encryption | API logs and manifests |
| Controllers behave inconsistently | Stale revision/watch state | Revision bump/compaction review |
| Secrets unreadable | Missing encryption provider key | Protected key recovery |
| Pods Running but application broken | Missing PVC/external dependency | Data and dependency validation |
| Backup job succeeded but no restore | Untested procedure | Isolated recovery drill |

## 17. Production runbook

### Detect and classify

1. Record customer impact and incident timeline.
2. Inspect API readiness and etcd member health.
3. Confirm network/TLS/storage conditions and quorum.
4. Determine repair versus disaster-recovery decision.
5. Assign incident commander, etcd operator and security owner.

### Recover (approved self-managed clusters only)

1. Preserve evidence and stop destructive/competing automation.
2. Verify backup integrity, timestamp and encryption keys.
3. Calculate RPO gap and obtain business approval if exceeded.
4. Prepare new logical etcd cluster and isolated recovery topology.
5. Restore with appropriate revision/watch safeguards.
6. Start control-plane components according to the topology runbook.
7. Validate API, controllers, workloads, data dependencies and SLIs.
8. Approve traffic cutover; document measured RPO/RTO.

### Prevent

- Scheduled encrypted snapshots and off-host copies.
- Restore drills at defined cadence.
- Quorum, disk, WAL, TLS and backup-age monitoring.
- Version-controlled runbooks and key recovery tests.
- Periodic review of failure-domain separation and RPO requirements.

## 18. Security and operational safeguards

- Restrict etcd client certificates to authorized operators.
- Protect snapshot files as sensitive cluster data.
- Do not copy `/etc/kubernetes/pki` to unsecured locations.
- Keep backup deletion privileges separate from backup creation.
- Validate encryption-at-rest provider keys and rotation recovery.
- Avoid direct production changes from unreviewed tutorials.
- Never perform a live production etcd restore without approved disaster declaration and topology-specific runbook.

## 19. Chapter acceptance checklist

- [ ] Managed versus self-managed etcd boundary established.
- [ ] Cluster topology and quorum model documented.
- [ ] Member health, endpoint and TLS inventory completed.
- [ ] Snapshot procedure and off-host protection reviewed.
- [ ] Snapshot metadata and hash verification documented.
- [ ] Isolated restore design approved.
- [ ] Version-specific revision bump/compaction behavior assessed.
- [ ] Control-plane and application recovery gates defined.
- [ ] Encryption keys and sensitive snapshot handling reviewed.
- [ ] RPO/RTO measured or explicitly marked not tested.
- [ ] Quorum-loss tabletop completed.
- [ ] Restore drill evidence and independent review recorded.
- [ ] Runtime validation completed before marking Lab Validated.

## 20. Cleanup

The read-only diagnostics require no cleanup. In the disposable restore lab, stop only the lab-owned etcd process, preserve evidence as required, and remove temporary restored data directories **only after verifying their location and owner approval**. Never delete a production etcd data directory or snapshot as tutorial cleanup.

**Status:** Draft — runtime validation and independent technical review pending.

## 21. References

- [etcd Disaster Recovery](https://etcd.io/docs/v3.5/op-guide/recovery/)
- [etcd Backup and Restore](https://etcd.io/docs/v3.5/op-guide/recovery/#snapshotting-the-keyspace)
- [etcd Runtime Reconfiguration](https://etcd.io/docs/v3.5/op-guide/runtime-configuration/)
- [Kubernetes Operating etcd Clusters](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/)
- [Kubernetes Encryption at Rest](https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/)
- [Kubernetes High Availability Topologies](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/ha-topology/)
- [Amazon EKS Documentation](https://docs.aws.amazon.com/eks/)
- [Azure AKS Documentation](https://learn.microsoft.com/en-us/azure/aks/)

**Next:** Chapter 073 — Velero and Persistent Volume Backups.
