# Chapter 052 — etcd Operations, Quorum and Recovery

**Track:** Kubernetes Administration · **Part 11 — High Availability and Disaster Recovery**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators and platform engineers  
**Prerequisites:** Chapter 051; kubectl, Windows PowerShell; approved self-managed etcd lab or provider documentation

## 1. Production incident scenario

A three-voter etcd cluster backs a highly available Kubernetes control plane. One member becomes unhealthy as disk fsync latency rises. Another control-plane host is scheduled for maintenance. The SRE must preserve quorum, diagnose the degraded member, verify backup integrity, and choose between member recovery and disaster recovery without creating split-brain or losing Kubernetes state.

**Goal:** operate etcd safely, understand Raft quorum and failure modes, perform an isolated snapshot-and-restore rehearsal, and produce an evidence-based recovery runbook. **No production etcd mutations are performed by this tutorial.**

### Learning objectives

1. Explain etcd's role as the Kubernetes API server's persistent state store.
2. Calculate Raft voting quorum and failure tolerance.
3. Identify etcd membership, leadership, latency, storage and alarms.
4. Distinguish member recovery with quorum from full-cluster disaster recovery.
5. Create, verify and restore snapshots in a disposable environment.
6. Evaluate compaction, defragmentation and space-quota operations safely.
7. Build alerting, backup, RPO/RTO and incident acceptance criteria.

## 2. etcd architecture and Kubernetes integration

```text
kubectl / controllers / kubelets
              |
       kube-apiserver
              |
       etcd client API
              |
  +-----------+-----------+
  |           |           |
etcd-1      etcd-2      etcd-3
 AZ-a        AZ-b        AZ-c
  +----- Raft quorum -----+
              |
     Kubernetes cluster state
```

Only the API server should normally access the Kubernetes etcd backend. etcd stores sensitive Kubernetes data, including Secret objects unless application-level encryption at rest is configured. Protect member certificates, endpoints, data directories and snapshots as sensitive infrastructure.

### Raft fundamentals

An etcd cluster elects a leader; committed writes require agreement by a majority of voting members. The leader may change during faults. A minority partition must not continue committing writes. Network latency and durable disk writes affect proposal and commit latency.

| Voting members | Majority quorum | Simultaneous voter failures tolerated |
|---:|---:|---:|
| 1 | 1 | 0 |
| 2 | 2 | 0 |
| 3 | 2 | 1 |
| 4 | 3 | 1 |
| 5 | 3 | 2 |
| 7 | 4 | 3 |

**Formula:** quorum = floor(N/2) + 1; tolerated failures = N - quorum. Adding a fourth voting member to three does not increase tolerated failures. Learner/nonvoting members have different semantics and must not be counted as voters.

## 3. Safety prerequisites and access boundaries

Core cluster labs are read-only. The snapshot/restore lab is **strictly limited to a disposable etcd instance or isolated training environment**. Do not expose etcd ports to the public internet. Never copy live etcd TLS private keys into shell history, chat, tickets or repositories.

```powershell
kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
kubectl -n kube-system get pods -o wide
kubectl get --raw /readyz
```

Managed EKS/AKS/GKE control-plane etcd is not generally exposed to customers. Use provider-managed recovery guarantees and metrics; do not assume host access or run etcdctl against provider infrastructure.

## 4. Lab 1 — Determine etcd ownership and topology

```powershell
kubectl get nodes -l node-role.kubernetes.io/control-plane -o wide
kubectl -n kube-system get pods -o wide
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get --raw /readyz
```

**Expected:** self-managed clusters may expose static etcd Pods and control-plane Nodes; managed clusters may expose neither. Record cluster type, stacked/external etcd topology, voting members, AZ placement, backup ownership and monitoring sources. **Absence of etcd Pods in a managed cluster does not mean etcd is absent.**

## 5. Lab 2 — Inspect etcd endpoint and member health

On an **authorized self-managed control-plane host**, use the installed etcd client and approved TLS files. The paths below are common kubeadm defaults and must be verified against the actual manifest. Never paste the certificate key contents.

```bash
export ETCDCTL_API=3
ETCDCTL='etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt --key=/etc/kubernetes/pki/etcd/healthcheck-client.key'
$ETCDCTL endpoint health
$ETCDCTL endpoint status --write-out=table
$ETCDCTL member list --write-out=table
$ETCDCTL alarm list
```

**Expected:** endpoint health, leader/member IDs, Raft term/index, database size and active alarms. **Caution:** a local endpoint check tests only that endpoint; a full cluster assessment should query every approved member endpoint. The example assumes shell expansion of a command string; for scripts prefer an array or direct etcdctl invocation to avoid quoting ambiguity.

### Interpret evidence

- One failed endpoint but quorum healthy: investigate host, network, TLS, disk and member state.
- No leader / quorum lost: freeze maintenance and initiate approved disaster recovery assessment.
- High leader changes: investigate latency, packet loss, CPU scheduling and disk stalls.
- NOSPACE alarm: inspect backend quota and fragmentation before a reviewed remediation.
- High applied/committed index lag: investigate member performance and network.

## 6. Lab 3 — Analyze storage, WAL and performance

On an authorized Linux etcd host, use read-only OS checks:

```bash
df -h
df -i
sudo journalctl -u etcd --since '30 minutes ago' --no-pager
sudo iostat -xz 1 3
```

**Expected:** disk usage, inode usage, service logs and I/O latency where tools/services exist. In kubeadm stacked-etcd installations, etcd may run as a static Pod rather than a systemd service; use approved container runtime or logging access instead.

### Important performance signals

| Signal | Risk | Investigation |
|---|---|---|
| WAL fsync latency | Slow durable writes | Disk IOPS/latency, noisy neighbors |
| Backend commit latency | Delayed state persistence | Disk throughput and stalls |
| Leader changes | Instability | Network, CPU, disk and timeouts |
| Proposal failures | Write availability | Quorum and member health |
| Database size/quota | NOSPACE alarms | Compaction and fragmentation |
| Network RTT | Consensus delays | Cross-AZ links and packet loss |
| CPU/memory saturation | Slow member responses | Node and container metrics |

Do not assume a low average disk latency rules out damaging p99 fsync spikes. etcd is sensitive to durable storage latency and reliable networking.

## 7. Lab 4 — Verify snapshot backup design

On a **self-managed etcd cluster with approved backup access**, an authorized administrator can create a snapshot using etcdctl and appropriate TLS credentials. The example below is a *template*, not an instruction to run against production:

```bash
ETCDCTL_API=3 etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key \
  snapshot save /secure-backups/etcd-snapshot.db
```

Inspect the snapshot with the supported `etcdutl snapshot status` command (etcd version dependent):

```bash
etcdutl snapshot status /secure-backups/etcd-snapshot.db --write-out=table
```

**Expected:** snapshot metadata is available, but a successful status command alone is **not a restore test**. Encrypt snapshots at rest and in transit, restrict access, and store copies outside the cluster's failure domain. Define backup cadence from RPO and prove restoration against an isolated environment.

### Backup acceptance

1. Record snapshot timestamp, source cluster, etcd version and revision.
2. Protect snapshot confidentiality; it can contain Kubernetes Secrets.
3. Validate snapshot file integrity and retention.
4. Test restore into a separate environment.
5. Verify API resources, controllers, admission, encryption configuration and dependent applications after recovery.

## 8. Lab 5 — Isolated snapshot-and-restore rehearsal

**Never restore an etcd snapshot into a running production cluster as a tutorial exercise.** Use a disposable VM/container and the same compatible etcd/etcdutl release. A minimal standalone example:

```bash
# On an isolated training machine with etcd, etcdctl and etcdutl installed
mkdir -p /tmp/ch052
etcd --name ch052 --data-dir /tmp/ch052/live \
  --listen-client-urls http://127.0.0.1:12379 \
  --advertise-client-urls http://127.0.0.1:12379 \
  --listen-peer-urls http://127.0.0.1:12380 \
  --initial-advertise-peer-urls http://127.0.0.1:12380 \
  --initial-cluster ch052=http://127.0.0.1:12380 \
  --initial-cluster-state new
```

Run that process in a dedicated terminal, then in another terminal:

```bash
ETCDCTL_API=3 etcdctl --endpoints=http://127.0.0.1:12379 put /training/ch052 'snapshot-test'
ETCDCTL_API=3 etcdctl --endpoints=http://127.0.0.1:12379 get /training/ch052
ETCDCTL_API=3 etcdctl --endpoints=http://127.0.0.1:12379 snapshot save /tmp/ch052/snapshot.db
etcdutl snapshot status /tmp/ch052/snapshot.db --write-out=table
```

Stop the disposable etcd process **before** restoring. Restore to a **different** data directory:

```bash
etcdutl snapshot restore /tmp/ch052/snapshot.db \
  --name ch052-restored \
  --data-dir /tmp/ch052/restored \
  --initial-cluster ch052-restored=http://127.0.0.1:22380 \
  --initial-advertise-peer-urls http://127.0.0.1:22380
etcd --name ch052-restored --data-dir /tmp/ch052/restored \
  --listen-client-urls http://127.0.0.1:22379 \
  --advertise-client-urls http://127.0.0.1:22379 \
  --listen-peer-urls http://127.0.0.1:22380 \
  --initial-advertise-peer-urls http://127.0.0.1:22380 \
  --initial-cluster ch052-restored=http://127.0.0.1:22380 \
  --initial-cluster-state new
```

From another terminal:

```bash
ETCDCTL_API=3 etcdctl --endpoints=http://127.0.0.1:22379 get /training/ch052
```

**Expected:** the value `snapshot-test` is recovered. These loopback-only HTTP endpoints are for disposable local training **only**; production etcd must use authenticated TLS and tightly restricted network access. Snapshot restore semantics, revision bump and compaction marks matter for Kubernetes informer caches; follow current official Kubernetes/etcd disaster recovery guidance for a real cluster.

## 9. Lab 6 — Compaction, defragmentation and quota tabletop

**No mutation is executed in this lab.**

### Key distinctions

- **Compaction:** removes obsolete historical revisions, subject to etcd retention semantics.
- **Defragmentation:** reclaims physical backend space after compaction; can temporarily block member operations and requires careful sequencing.
- **NOSPACE alarm:** prevents normal writes; remediation requires identifying backend size, compaction/defrag needs and safe alarm disarm procedure.
- **Snapshot:** captures etcd data at a point in time; does not replace ongoing quorum health.

### Decision exercise

A three-member etcd cluster has quorum but one member is slow and the backend is near quota. Document the safe sequence: confirm backup, capture alarms and metrics, inspect disk latency, assess compaction state, perform approved per-member maintenance without losing quorum, validate health between members, and clear alarms only after resolving the underlying condition. Never defragment all members concurrently during a production incident.

## 10. Lab 7 — Quorum-loss incident simulation tabletop

**Scenario:** one of three etcd members is down. A second member shows severe fsync latency and is about to be rebooted for patching. A team member suggests removing the failed member and immediately restoring a snapshot.

### Required response

1. Freeze patching and any action that could remove another voter.
2. Verify the two surviving voters can still elect/maintain a leader and commit proposals.
3. Determine whether the unhealthy member has disk, network, CPU or TLS issues.
4. Preserve logs, member IDs, cluster IDs, leader/term and backup metadata.
5. Recover the failed member using the **quorum-preserving** member replacement procedure if required.
6. Do not use snapshot restore when quorum is healthy and normal member recovery is possible.
7. If quorum is genuinely lost, invoke the reviewed disaster-recovery procedure with RPO/RTO approval and verified snapshots.
8. Validate API server state, workloads, certificates, controllers and reconciliation after recovery.

**Expected:** a decision record that differentiates a degraded but quorate cluster from a lost-quorum disaster. Never force new cluster formation from stale data without explicit recovery authorization.

## 11. Member recovery versus disaster recovery

| Condition | Preferred approach | Key guardrail |
|---|---|---|
| One voter down, quorum healthy | Repair or replace member | Keep majority online |
| Slow voter, quorum healthy | Diagnose I/O/network | Do not restart another voter |
| Leader changes but majority available | Stabilize infrastructure | Avoid disruptive member churn |
| Quorum lost | Approved disaster recovery | Restore from verified source; assess data loss |
| Corrupt member data, quorum healthy | Replace damaged member | Never copy arbitrary peer data directories |
| All data lost | Rebuild from trusted backup | RPO/RTO and external reconciliation |

**Do not equate an etcd member replacement with a snapshot restore.** Member replacement uses surviving cluster state when quorum remains; disaster recovery may reset membership and restore historical state.

## 12. Monitoring and alert design

| Signal | Purpose |
|---|---|
| etcd server has leader | Detect missing consensus leader |
| etcd leader changes | Detect election instability |
| etcd WAL fsync duration | Detect durable I/O bottleneck |
| etcd backend commit duration | Detect persistence delays |
| etcd DB total size / quota | Predict NOSPACE risk |
| etcd proposal failures | Detect write failures |
| Peer RTT and network errors | Diagnose partitions/latency |
| Snapshot age and restore-test age | Measure recoverability |
| API server write latency/errors | Detect user-visible control-plane impact |

Metric names and availability vary by etcd/Kubernetes/provider version. Use documented metrics for the deployed release and tune thresholds against measured baseline and SLOs.

## 13. Production incident runbook

### Detect and scope

1. Confirm API error rates, etcd leader/health, disk latency and member status.
2. Identify voting member count, healthy voters, current leader and zone topology.
3. Determine whether quorum is preserved; freeze planned maintenance if uncertain.

### Contain

1. Protect surviving voting members and block concurrent restarts.
2. Capture diagnostics and snapshot inventory without exposing credentials.
3. Escalate storage/network infrastructure if fsync/RTT indicates a shared failure.

### Recover with quorum

1. Repair infrastructure or replace the failed member through a reviewed version-specific procedure.
2. Validate membership, leader stability, proposal commits and API server health.
3. Confirm control-plane reconciliation and application health.

### Recover after quorum loss

1. Declare disaster recovery and obtain RPO/RTO/data-loss approval.
2. Select verified backup and determine revision/watch-cache implications.
3. Restore using the official etcd/Kubernetes workflow appropriate to topology.
4. Validate control-plane certificates, encryption config, API objects, controllers and workloads.
5. Reconcile external cloud resources, persistent volumes and applications against restored cluster state.

### Close

Document incident timeline, member IDs, quorum state, backup timestamp, possible data loss, recovered API SLIs and corrective actions.

## 14. Troubleshooting matrix

| Symptom | Candidate cause | Safe next check |
|---|---|---|
| No leader | Quorum/network partition | Member and peer reachability |
| Frequent elections | Disk/network stalls | WAL fsync, RTT, CPU |
| API writes slow | etcd backend latency | Commit duration, disk |
| NOSPACE alarm | Backend quota | DB size, compaction state |
| TLS handshake failure | Cert expiry/SAN/CA | Public cert metadata and trust |
| Snapshot save fails | Disk/access/connectivity | Filesystem, endpoint, permissions |
| Restore starts but API broken | Revision/config mismatch | Restore runbook and API logs |
| Member health fails | Host/network/etcd process | Host logs and peer metrics |

## 15. Cleanup

Stop the isolated etcd training processes before removing disposable data. Never delete real etcd data directories or Kubernetes control-plane PKI as cleanup.

```bash
# Only after stopping both disposable etcd processes
rm -rf /tmp/ch052
```

## 16. Acceptance checklist

- [ ] etcd ownership and topology identified.
- [ ] Voting quorum calculated correctly.
- [ ] Member health, leader and alarms interpreted.
- [ ] WAL fsync, backend commit and network signals assessed.
- [ ] Snapshot confidentiality, retention and restore requirements documented.
- [ ] Disposable snapshot restore rehearsed without touching production.
- [ ] Compaction, defrag and NOSPACE operations distinguished.
- [ ] Member recovery and lost-quorum disaster recovery distinguished.
- [ ] Incident runbook, RPO/RTO and monitoring ownership recorded.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Status:** Draft — runtime validation and technical review pending.

## 17. References

- [Operating etcd Clusters for Kubernetes](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/)
- [Kubernetes HA Topology](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/ha-topology/)
- [etcd Operations Guide](https://etcd.io/docs/v3.5/op-guide/)
- [etcd Disaster Recovery](https://etcd.io/docs/v3.5/op-guide/recovery/)
- [etcd Maintenance](https://etcd.io/docs/v3.5/op-guide/maintenance/)
- [etcd Metrics](https://etcd.io/docs/v3.5/metrics/)

**Next:** Chapter 053 — PodDisruptionBudgets and Graceful Shutdown.