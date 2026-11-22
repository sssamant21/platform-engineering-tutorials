# V05 — Stateful-workload HA failure-injection acceptance (draft)

**Scope:** Chapter 017, platform engineering / DBRE / application owners. **Status:** Review protocol authored; no test executed, no independent approval. This is not a production failover runbook.

## Objective and safety boundary

Demonstrate in an **isolated, disposable, approved** OpenShift environment that stateful workload availability and data correctness are preserved under controlled failure scenarios. Kubernetes pod readiness or successful rescheduling alone does **not** establish database quorum, single-writer safety, transaction durability, or acceptable RPO/RTO.

Do not perform failure injection, node drain, forced pod deletion, storage detachment, fencing, or database promotion in production as part of this tutorial. Production incidents require their own incident commander, workload owner, approved change/incident process and vendor-supported recovery procedure.

## Prerequisites and ownership

- Record exact OpenShift release, platform/provider, topology, zones, MachineConfigPools, storage driver/CSI version, and whether the cluster is managed or self-managed. Confirm support for the exact version and topology before approving a scenario.
- Use a disposable namespace and test dataset; no production credentials, data, PVCs or endpoints. Confirm the identity and API server/context against the approved test-cluster inventory.
- Require named platform/SRE owner, database/application owner, storage owner, and observer; agree in advance on stop conditions, recovery authority and evidence retention.
- Establish a **tested** recovery path and clean baseline: workload-native backup/restore (or snapshot with verified consistency semantics), independent data-integrity verification, fencing/single-writer controls, and a measured baseline.
- Define application-specific RPO, RTO, availability and correctness thresholds **before** tests. Avoid inventing universal acceptable values.
- Preflight read permissions separately: `list` pods, StatefulSets, PVCs, PDBs, events in the test namespace; `list` nodes, StorageClasses and PVs only where approved. `oc auth can-i` checks are advisory and do not replace handling `Forbidden` from the actual read.

## Read-only baseline (Bash or PowerShell, authorized test namespace)

```sh
oc whoami
oc config current-context
oc version
oc auth can-i list pods -n "$TEST_NS"
oc auth can-i list statefulsets.apps -n "$TEST_NS"
oc auth can-i list persistentvolumeclaims -n "$TEST_NS"
oc auth can-i list poddisruptionbudgets.policy -n "$TEST_NS"
```

For PowerShell, set `$TestNs` to the approved namespace and use `-n $TestNs` instead of `-n "$TEST_NS"`. **Do not execute the following inventory until identity, context, and individual authorization checks are verified.** If any permission is denied or indeterminate, skip that read and escalate; never elevate privileges merely to complete a tutorial.

```sh
oc get pods -n "$TEST_NS" -o wide
oc get statefulsets.apps -n "$TEST_NS"
oc get pvc -n "$TEST_NS"
oc get pdb -n "$TEST_NS"
```

Record the actual exit status and sanitized output for each authorized command. Expected baseline: all intended replicas ready, storage bound, workload-native cluster healthy, correct leader/replica roles, no outstanding replication lag outside the approved threshold. These are **acceptance criteria**, not observed results.

## Scenario matrix (approval-only; no destructive commands supplied)

| Scenario | Preconditions | Required observations | Stop / reject condition |
| --- | --- | --- | --- |
| Single application-pod loss | Healthy redundancy; confirmed owner-approved method | Client errors, leader election, write correctness, recovery duration | Dual writer, data loss, quorum unavailable beyond approved limit |
| Node unavailable | Test-only node, topology and scheduling headroom | Placement, PVC reattachment, PDB behavior, replica quorum | Storage multi-attach, zone-wide placement collapse, lost fencing |
| Zone / failure-domain isolation | Multi-zone test topology and owner-approved simulator | Independent failure domains, application quorum, DNS/client recovery | No surviving majority, inconsistent writes, unsupported storage topology |
| Storage-path interruption | CSI/provider-approved isolated test | Mount/attach events, write durability, recovery and consistency | Split-brain, irreversible volume action, corrupted or stale data |
| Application leader failover | Workload-native fencing and independent observer | Exactly one writer, acknowledged-write durability, replication catch-up | Two writable primaries, unverified promotion, missing audit evidence |

PDBs restrict **voluntary** disruptions through the eviction API; they do not guarantee protection from involuntary node loss. Storage snapshots do not by themselves prove database-consistent recovery. OpenShift etcd backup does not replace application data backup.

## Evidence and acceptance

Record test ID, immutable code/config revisions, UTC start/end, approved change reference, actual cluster and workload versions, preflight results, injected fault method, precise measured RPO/RTO, client-visible errors, application-native replication/quorum evidence, integrity checks, storage events, recovery steps, operator signoffs, and sanitized logs. Mark each scenario **PASS / FAIL / SKIP / BLOCKED**; a skipped or blocked scenario is never PASS.

After each test, verify all replicas healthy, no unauthorized writer, stable PVC attachment, zero unapproved data divergence, monitoring restored and explicit owner signoff. Revert only via the **preapproved** scenario-specific recovery plan; do not assume that reversing a Kubernetes manifest or restarting a pod reverses data loss.

## Review gates

1. Platform reviewer checks OCP release applicability, namespace and cluster-scoped RBAC, topology and disruption behavior.
2. Storage reviewer checks CSI support, reclaim policy, volume attachment and snapshot/restore consistency.
3. Database owner validates quorum, fencing, durability and backup/recovery; application owner validates end-to-end client correctness.
4. Security reviewer checks credential isolation, sanitized evidence and access expiry.
5. Change authority independently approves any production adaptation. This worksheet **never** constitutes production approval.

**Reference baseline:** [Red Hat OpenShift 4.22 documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22). Consult the matching version-specific storage, node, monitoring and backup sections and each database vendor's supported HA procedure before executing any isolated scenario.

Related: Chapter 017 stateful workload documentation (locate from the track index); [progress tracker](../PROGRESS-TRACKER.md).
