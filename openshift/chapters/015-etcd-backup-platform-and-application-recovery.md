# Chapter 015 — etcd Backup, Platform Recovery and Application Data Protection

**Audience:** Platform administrators, SREs and DBREs · **Duration:** ~60 minutes · **Baseline:** OpenShift Container Platform 4.22 · **Status:** Drafted; not runtime-tested or production-approved.

## Objectives and prerequisites (10 minutes)
Explain the boundary between an etcd control-plane snapshot and workload data protection; identify supported recovery choices; build an auditable RPO/RTO decision. Prerequisites: approved read-only access to cluster status, nodes and ClusterOperators; knowledge of cluster installation type and control-plane topology; a documented backup owner and protected storage destination. Recovery execution requires separate elevated privileges, change approval and a Red Hat-supported procedure for the **exact installed release**.

**Safety:** An etcd snapshot is not a backup of persistent volume contents, external databases, container registries or application secrets stored outside etcd. A snapshot can contain sensitive Kubernetes resources, including Secrets: treat snapshot archives and accompanying static resources as highly confidential. Do not download, print, commit, or attach snapshots to tickets. Never execute `cluster-backup.sh`, `cluster-restore.sh`, force-quorum recovery, node deletion, or etcd member operations as part of this read-only chapter.

## Architecture and recovery boundaries (15 minutes)
- etcd holds Kubernetes/OpenShift API state. Supported control-plane recovery depends on topology, platform, health, snapshot freshness, and version-specific Red Hat procedures.
- A complete supported etcd backup workflow normally involves the control-plane snapshot **and** required static pod resource artifacts; retain them together according to the Red Hat procedure. An arbitrary `etcdctl snapshot save` is **not** a substitute for the documented OCP workflow.
- Application continuity additionally needs CSI/storage snapshots or application-consistent backups, database WAL/oplog/log retention as appropriate, encryption-key and external-dependency recovery, and restore testing. VolumeSnapshots are not universally available; verify the CSI driver and policy.
- Distinguish single control-plane node recovery, lost control-plane quorum, and full cluster recovery. These are different playbooks. A healthy cluster is not a candidate for speculative restore.
- RPO is maximum tolerable data loss; RTO is maximum tolerable service recovery time. Record separate platform API and application/database targets. Do not promise a measured RPO/RTO without a timed rehearsal.

## Read-only assessment (15 minutes)
Confirm the intended cluster/context **without displaying kubeconfig or tokens**:
```sh
oc whoami
oc config current-context
oc version
oc get clusterversion
oc get co
oc get nodes -l node-role.kubernetes.io/master
oc get mcp
oc get infrastructure cluster -o jsonpath='{.status.platformStatus.type}{"\n"}'
```
On PowerShell, run the same `oc` commands. For more detail, inspect only authorized resources (`oc auth can-i get clusterversion`, `oc auth can-i list nodes`). `Forbidden` is an RBAC boundary, not evidence of a broken cluster. Managed/control-plane-hosted variants may not expose the same recovery controls: verify the provider-supported process first.

**Backup inventory worksheet (do not include secrets):** cluster alias; installed OCP version; platform/topology; last backup time and age; backup and static-resource pair presence (yes/no, without paths/contents); encrypted off-cluster retention and access owner; restore-test date; application backup owner; RPO/RTO targets; approval ticket; gaps.

## Decision exercise (10 minutes)
Scenario A: one worker node NotReady, control plane healthy — investigate node; **do not restore etcd**.
Scenario B: ClusterOperator degraded but API reachable — triage root cause; **do not assume restore**.
Scenario C: confirmed loss of etcd quorum — declare incident, preserve evidence, contact platform owner/Red Hat support, determine exact supported recovery path and impact before any state change.
Scenario D: PostgreSQL PVC lost but OCP control plane healthy — application/storage recovery, **not** etcd restore.
Scenario E: snapshot older than accepted RPO — document unmet recovery objective; do not assert recoverability.

## Change gates and validation (10 minutes)
Before any restore: incident commander and change approval, supported release-specific recovery guide, quorum/topology diagnosis, verified backup artifact integrity and compatible release, protected credentials, data-owner sign-off, business-impact assessment, workload recovery sequencing, communications and stop conditions. A restore is not a simple reversible rollback; recovering the previous state may require separate backups and can lose newer API changes. Rehearse only in isolated, explicitly authorized environments.

After an approved recovery, independently validate API availability, ClusterVersion/ClusterOperators, nodes/MCPs, storage attachment, Routes/DNS, RBAC, monitoring and application/database consistency. Record timestamps, actual RPO/RTO and reviewer. Escalate immediately on missing artifacts, failed integrity checks, unsupported topology, unknown backup age, or database consistency uncertainty.

## Expected observations and common errors
- `oc get co`: Available/Progressing/Degraded conditions vary by cluster; investigate abnormal values rather than assuming all outputs are identical.
- `Error from server (Forbidden)`: request authorized read-only role; do not elevate yourself.
- `Unable to connect to the server`: confirm context/network/API availability before drawing conclusions.
- No backup inventory: **backup assurance unknown**, not “backup passed”.
- Snapshot exists but no restore rehearsal: **restore not validated**.

## Further reading
- [OCP 4.22 documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22)
- [OCP 4.22 Backup and restore](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/backup_and_restore/)
- [OCP 4.22 Support and troubleshooting](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/support/)
- [Kubernetes fundamentals in this repository](../../../kubernetes/README.md)

Continue with [Lab 015](../labs/015-recovery-read-only-readiness-audit.md) and [Recovery readiness runbook](../runbooks/etcd-backup-recovery-readiness-triage.md).
