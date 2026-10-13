# Chapter 102 — Deploy a Highly Available Stateful Application

**Track:** Kubernetes Administration · **Part 21 — Final Enterprise Kubernetes Capstone**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** Kubernetes administrators, SREs, DBREs, platform engineers  
**Prerequisites:** Chapters 016–020, 036–045, 071–075, 096, 101; an approved disposable multi-zone Kubernetes cluster, kubectl, PowerShell, GitOps, a supported CSI driver and VolumeSnapshot implementation where available.

## Mission

Deploy a production-*style* stateful service and demonstrate availability, replication, durable storage, backup, failover, recovery and operational readiness. The reference implementation uses **PostgreSQL managed by a supported Kubernetes database operator** with an approved version and image. Operator-specific CRD names and fields vary: use the vendor's pinned, tested examples rather than inventing portable operator YAML.

**Safety:** execute on disposable, non-sensitive data. No exercise authorizes a production primary failover, PVC deletion, unsafe finalizer removal or destructive storage test.

## 1. Stateful HA architecture

```text
Client → Application → read/write Service → PostgreSQL primary
                                          |         |
                                          |     WAL streaming
                                          |         v
                                          +-- Replica A (Zone B)
                                          +-- Replica B (Zone C)
                                                    |
                                   CSI volumes / snapshots
                                                    |
                            DB-native backups → object storage
                                                    |
                              Monitoring + operator + GitOps
```

A StatefulSet supplies stable Pod identity and storage attachment semantics; **it does not implement database replication, leader election, fencing, backup or consistency**. Use a database-aware operator with documented HA semantics or an approved managed database service. For this capstone, choose a supported operator and record its actual behavior.

## 2. Requirements and acceptance contract

Define before installation:
- Availability and p95 latency SLO.
- RTO and RPO targets.
- Consistency requirements and acceptable transaction loss.
- Write/read workload profile, peak connections and data growth.
- Failure domains and minimum healthy replicas.
- Backup retention, encryption, restore location and ownership.
- Supported operator/database/Kubernetes versions.
- Change window, rollback plan, cost budget and escalation.

For PostgreSQL, asynchronous replication can lose acknowledged transactions during an unplanned failover; synchronous replication changes availability/latency tradeoffs. **Do not promise zero data loss without an architecture and test evidence that supports it.**

## 3. Lab 01 — Inventory the target cluster

```powershell
kubectl config current-context
kubectl get nodes -o wide
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get storageclass
kubectl get csidrivers
kubectl get pdb -A
kubectl get events -A --sort-by=.lastTimestamp
```

Confirm distinct zones, storage topology, free capacity, cloud quotas and CSI health. If the environment lacks multi-zone support, label the exercise as single-failure-domain and do not claim zone-level HA.

## 4. Lab 02 — Design the database topology

Choose one primary and at least two replicas when supported by the operator and budget. Specify synchronous/asynchronous replication, WAL retention, replication slots, read routing, primary service behavior, failover quorum and fencing. Document how the operator avoids split brain and what happens during API server unavailability.

**Evidence:** diagram, operator release/support matrix, storage-class parameters and the expected recovery path for node, zone and primary failure.

## 5. Lab 03 — Namespace, identity and resource governance

Create an approved GitOps-managed namespace, scoped ServiceAccounts, NetworkPolicies, ResourceQuota and LimitRange. Define CPU/memory requests, storage requests and Pod Security Admission expectations.

```powershell
kubectl create namespace stateful-lab --dry-run=client -o yaml
kubectl get resourcequota,limitrange -n stateful-lab
kubectl get networkpolicy -n stateful-lab
kubectl auth can-i get secrets -n stateful-lab
```

The create command above **prints a manifest only**. Apply through the approved GitOps workflow. Avoid committing passwords or unencrypted connection strings.

## 6. Lab 04 — Install a supported PostgreSQL operator

Select an organization-approved operator such as CloudNativePG, Crunchy Postgres for Kubernetes or another supported implementation. Pin versions and verify compatibility with your Kubernetes version, PostgreSQL major version, CSI, admission policies and backup integration.

Inventory installed resources:

```powershell
kubectl get crds
kubectl get deployments -A
kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations
kubectl get serviceaccounts -A
kubectl get events -A --sort-by=.lastTimestamp
```

Review operator RBAC, namespace watch scope, webhook certificates, image provenance, leader election and metrics. **Do not install two controllers that both manage the same database cluster.**

## 7. Lab 05 — Deploy the HA database custom resource

Use the chosen operator's **version-matched example** for a three-instance PostgreSQL cluster. Configure:
- Persistent storage size and StorageClass.
- Requests/limits sized for workload and replication.
- Pod anti-affinity/topology spread across available zones.
- TLS and authentication through approved secret management.
- Backup repository and retention.
- Primary/read-only service discovery.
- Failover and maintenance policy supported by the operator.

```powershell
kubectl apply --dry-run=server -f .\postgres-cluster.yaml
kubectl get pods,pvc,svc -n stateful-lab -o wide
kubectl get events -n stateful-lab --sort-by=.lastTimestamp
```

`postgres-cluster.yaml` must be obtained from the selected operator's official versioned documentation and adapted before running. A generic `kind: PostgreSQL` manifest is **not portable** across operators.

## 8. Lab 06 — Verify storage and placement

```powershell
kubectl get pods -n stateful-lab -o wide
kubectl get pvc -n stateful-lab
kubectl get pv
kubectl describe pvc <postgres-pvc> -n stateful-lab
kubectl get nodes -L topology.kubernetes.io/zone
```

Verify each instance has a separate persistent volume and desired failure-domain placement. Check volume binding mode, reclaim policy, expansion, encryption and snapshot support. Replicas on separate nodes in the same zone do not satisfy zone-failure tolerance.

## 9. Lab 07 — Database replication and role verification

Use the operator's approved admin connection method, then execute PostgreSQL SQL:

```sql
SELECT pg_is_in_recovery();
SELECT application_name, client_addr, state, sync_state,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;
SELECT now(), pg_current_wal_lsn();
```

Run `pg_stat_replication` on the primary. On replicas, inspect `pg_stat_wal_receiver` and replay LSN; `pg_current_wal_lsn()` is not valid on a standby. Record primary identity, replication state, lag and the expected synchronous commit policy. Verify the operator's actual leader election/fencing behavior.

## 10. Lab 08 — Seed test data and validate consistency

Create disposable data:

```sql
CREATE TABLE IF NOT EXISTS ha_test (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  payload text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO ha_test(payload)
SELECT 'record-' || g FROM generate_series(1,1000) AS g;
SELECT count(*) FROM ha_test;
```

Read the dataset from primary and replicas using approved service endpoints. For asynchronous replicas, allow for replay lag before declaring a mismatch. Record transaction IDs/checksums and client-observed commit outcomes.

## 11. Lab 09 — Connection routing and application integration

Deploy a disposable client application that uses the operator-provided **write** service for transactions and a **read** service only where stale reads are acceptable. Test DNS, TLS validation, connection pooling, retries with jitter, transaction timeout and idempotency for retried writes.

Do not route writes to an arbitrary Pod IP or a replica. During failover, existing connections can break; clients must reconnect and re-resolve the primary endpoint.

## 12. Lab 10 — Probes, PDBs and disruption handling

```powershell
kubectl get pods -n stateful-lab -o yaml
kubectl get pdb -n stateful-lab
kubectl get events -n stateful-lab --sort-by=.lastTimestamp
```

Prefer operator-generated probes and PDBs; do not overwrite them without vendor guidance. Database readiness must reflect role/availability semantics, not simply an open TCP port. Ensure PDBs protect maintenance availability while understanding that they do not prevent all involuntary disruptions.

## 13. Lab 11 — Observability and baseline

Collect PostgreSQL connection saturation, transaction throughput, query latency, WAL generation, replication lag, replication slot retention, checkpoints, disk IOPS/latency, storage free space, CPU, memory, failover count and backup freshness.

```powershell
kubectl get pods -n stateful-lab
kubectl top pods -n stateful-lab
kubectl get events -n stateful-lab --sort-by=.lastTimestamp
```

Metrics Server is required for `top`. Alert on sustained lag, unavailable primary, disk exhaustion, backup failure and failed reconciliation. Correlate application errors with database metrics; a healthy operator Pod does not guarantee a healthy database.

## 14. Lab 12 — Planned switchover

Using the selected operator's **documented switchover command or CR mechanism**, move primary ownership in disposable staging. Record initial primary, operator events, client errors, transaction continuity and the new primary.

**Acceptance:** exactly one writable primary, replicas rejoin, clients reconnect, and measured downtime meets the defined objective. Do not substitute `kubectl delete pod` for a supported planned switchover procedure.

## 15. Lab 13 — Unplanned primary failure

After confirming backups and an approved stop plan, simulate failure of the primary **only using the operator's supported staging fault-injection procedure**. Measure detection, election/failover, fencing, application reconnection and any acknowledged writes missing after recovery.

**Stop immediately** if more than one writable primary is observed or data integrity becomes uncertain. Never run an unplanned primary kill against production as a tutorial exercise.

## 16. Lab 14 — Node and zone failure scenarios

Review scheduling and replica placement. In disposable staging, drain a single noncritical node only if operator documentation and PDBs permit it. For zone failure, use a controlled simulation or tabletop if cloud infrastructure disruption is unsafe.

```powershell
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get pods -n stateful-lab -o wide
kubectl get pdb -n stateful-lab
```

Distinguish node recovery, volume reattachment, replica rebuild and true zone loss. Zone-bound volumes may not attach in another zone; a surviving replica in a different zone may be required.

## 17. Lab 15 — Backups, PITR and restore validation

Configure supported database-native continuous backup/WAL archiving, with encryption, restricted object-store access and retention. Restore **to a separate test cluster or database**, not over the source.

Validate:
1. Base backup and required WAL segments exist.
2. Restore reaches the chosen point in time.
3. Table count/checksum matches the expected recovery point.
4. Database consistency and application connection checks pass.
5. RTO/RPO measured against the original objectives.
6. Keys, secrets and storage are independently recoverable.

Snapshots alone may not provide transaction-consistent PITR. Prefer operator/database-supported backup and recovery mechanisms.

## 18. Lab 16 — Rolling upgrade and version compatibility

Review the operator's supported PostgreSQL minor/major upgrade paths, container images, extension compatibility and rollback restrictions. Test a minor-version rolling update in disposable staging and verify replication, query correctness and service availability.

**Major upgrades** can require logical migration or a vendor-specific procedure and may be irreversible without a restore. A Helm rollback of the operator does not automatically downgrade PostgreSQL data files.

## 19. Lab 17 — Security, secrets and access recovery

Test TLS certificate validation, workload identity, network restrictions, RBAC, secret rotation and audit logging. Verify that a test identity without privileges cannot read database Secrets or execute arbitrary operator actions. Confirm recovery procedures do not expose passwords in terminal history or Git.

## 20. Lab 18 — Incident response and acceptance

| Scenario | Evidence | Acceptance |
|---|---|---|
| Pod restart | Role and PVC continuity | Data preserved |
| Planned switchover | Timeline and client errors | One writable primary |
| Primary failure | Election, fencing, RTO/RPO | No split brain; targets assessed |
| Replica lag | WAL/LSN metrics | Lag alert and recovery |
| Node/zone loss | Placement and storage behavior | Failure-domain objective met |
| Backup restore | PITR and checksums | Restored data correct |
| Rolling upgrade | Versions and query checks | Supported upgrade path |
| Secret rotation | Connection and authorization tests | Secure access maintained |

**Final acceptance checklist:**
- [ ] Operator and PostgreSQL versions pinned and reviewed.
- [ ] Multi-zone placement verified or limitation explicitly recorded.
- [ ] Replication, failover and fencing behavior demonstrated.
- [ ] Client reconnect and write safety validated.
- [ ] Data integrity checked before and after failures.
- [ ] Backup restore and PITR executed successfully.
- [ ] Observability and alert routing tested.
- [ ] Security controls and least privilege validated.
- [ ] Measured RTO/RPO compared with approved targets.
- [ ] Evidence independently reviewed and signed off.

## 21. Troubleshooting runbook

| Symptom | First checks | Recovery principle |
|---|---|---|
| No writable primary | Operator status, leader election, logs | Restore quorum/fencing before writes |
| Two primaries suspected | Role queries, connectivity, operator state | Stop writes; prevent split brain |
| Replica lag growing | WAL receiver, slots, IOPS, network | Fix bottleneck; protect WAL retention |
| PVC Pending | CSI, StorageClass, zone, quotas | Correct topology/provisioning |
| WAL storage filling | Replication slots, archiving, retention | Restore replication/archive safely |
| Failover succeeds but app errors | Pool, DNS, TLS, retries | Reconnect and validate transactions |
| Restore incomplete | Base backup, WAL, keys, timestamps | Retry from verified recovery chain |
| Operator unhealthy | RBAC, CRD versions, webhook, logs | Repair controller without deleting CRD |

## 22. Cleanup and handoff

Remove test workloads through GitOps, retain approved recovery evidence, and verify snapshots, object storage, disks and load balancers do not incur unwanted cost. Delete only explicitly disposable resources after confirming no shared PVCs or backups are affected. Preserve operator and application runbooks, ownership and change history.

## 23. Production takeaways

Kubernetes can schedule and restart stateful Pods, but database availability requires application-aware replication, durable storage, single-writer safety, backup/restore and client resilience. **A highly available StatefulSet is not automatically a highly available database.**

**Draft status:** the tutorial is published; labs, operator-specific manifests and recovery drills have not been executed or independently reviewed.

**Next:** Chapter 103 — Simulate Complex Kubernetes Failures.
