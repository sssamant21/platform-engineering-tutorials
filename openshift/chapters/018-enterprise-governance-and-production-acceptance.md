# Chapter 018 — Enterprise Governance and Production Acceptance

**Audience:** OpenShift platform admins, SREs and DBREs | **Duration:** ~60 minutes | **Baseline:** Red Hat OCP 4.22 | **Status:** Drafted; not lab-tested or production-approved.

## Learning objectives and prerequisites (10 minutes)

Define auditable operational ownership, change gates, least-privilege diagnostics, and production acceptance for an OpenShift cluster. Prerequisites: Chapters 001–017, authorized `oc` client and cluster access, an approved non-production or read-only production audit scope, and named platform, security, application and data owners. Review the [Kubernetes track](../../../kubernetes/README.md) for generic Kubernetes fundamentals; this chapter addresses OpenShift governance.

**Never paste kubeconfig, tokens, Secret data, raw support archives or patient/customer information into GitHub or tickets.** Confirm the exact cluster minor version and installation topology; supported commands and recovery paths are version-specific.

## Ownership and decision rights (15 minutes)

| Activity | Accountable decision owner | Responsible executor | Consult / approval |
| --- | --- | --- | --- |
| Cluster lifecycle, CVO, ClusterOperators, RHCOS/MCP, Machine API | Platform engineering | Authorized platform SRE | Change manager, security, application/data owners for impact |
| Namespace tenancy, RBAC/SCC policy | Platform security owner | Platform IAM/admin | Application owner, compliance |
| Capacity, monitoring, ingress, CSI platform services | Platform engineering | Platform SRE | Storage/network teams, app and DBRE |
| Database replication, backups, failover, recovery consistency | Data-service / DBRE owner | Database operator/DBRE | Application owner, platform, business continuity |
| Data retention and deletion policy | Business/data governance owner | Data team | Legal/compliance, application, DBRE |
| Application release and SLO | Application owner | Application team | Platform and DBRE |
| Incident severity, communication, restoration acceptance | Incident commander | Assigned responders | Impacted owners, change manager |
| Production change authorization | Designated change authority | Named change implementer | Platform, app, DBRE, security as applicable |

Accountability is an **organizational template**, not an OpenShift product default. Record named owners, backups, escalation path, on-call coverage and decision boundaries in the service catalog. Never infer that PVC snapshot or etcd backup alone provides application-consistent recovery.

## Minimum operational controls (10 minutes)

1. Inventory clusters, environment, version, topology, ownership, SLO, RPO/RTO and dependencies; restrict cluster identifiers in public artifacts.
2. Use federated identities and namespace-scoped RBAC where feasible. Separate observers, change approvers and implementers; time-limit privileged break-glass access and audit its use.
3. Require approved changes for upgrades, MCP changes, node drains, scaling, SCC/RBAC changes, storage deletion and failover. Require a tested backout or documented **forward-recovery** decision when rollback is unsupported.
4. Preserve baseline health and post-change evidence: `oc get clusterversion`, `oc get clusteroperators`, `oc get nodes`, `oc get mcp`, workload and application SLO checks.
5. Require independent approval for destructive/recovery actions and for claiming production readiness. Cluster rollback, etcd restore and database failover are not generic undo buttons.
6. Store sanitized evidence in controlled systems with retention and access rules. Review Red Hat's supported `must-gather` procedure before collecting: it may capture sensitive cluster configuration and requires elevated permissions.

## Acceptance checklist (10 minutes)

| Gate | Required evidence | Pass criterion |
| --- | --- | --- |
| Architecture | Version/topology, dependencies, support matrix | Reviewed against deployed OCP version |
| Access | Namespace RBAC/SCC matrix and break-glass audit | Least privilege and security signoff |
| Availability | Baseline CO/node/MCP status, service SLOs | Agreed service-specific thresholds met |
| Data safety | DB-native backup/restore, fencing, replica health | Independently measured RPO/RTO and data integrity |
| Change | Approved window, owners, go/no-go, stop conditions | Change record with backout/forward recovery |
| Operations | Alert routing, runbooks, paging, escalation | Owner acknowledgment and exercised response |
| Testing | Executed lab output, negative tests, timestamps | Genuine isolated/authorized evidence |
| Review | Named independent platform/security/DBRE reviewers | Signed approval; unresolved blockers tracked |

**Do not mark this learning path production-certified simply because all 18 chapters are written.**

## Change approval template (10 minutes)

Record: cluster/environment (sanitized); service impact; requester/implementer/approver; change ID; version/support references; affected Operators/nodes/tenants/databases; expected impact; backup currency and restore evidence; maintenance window/time zone; baseline metrics; stop/go thresholds; stepwise plan; rollback *feasibility* and forward-recovery alternative; validation owners; communication and incident bridge; closure evidence. Require a separate DBRE-approved failover/fencing plan for stateful services.

## Final review exercise (5 minutes)

Complete [Lab 018](../labs/018-governance-production-acceptance-read-only-audit.md), then use [Governance acceptance runbook](../runbooks/production-acceptance-and-change-gates.md) to classify any gaps. Expected result is a **documented readiness decision**, not a cluster modification.

## References

- [Red Hat OCP 4.22 documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22)
- [Red Hat OCP 4.22 support and diagnostic data collection](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html-single/support/index)
- [Red Hat OCP 4.22 authentication and authorization](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html-single/authentication_and_authorization/index)
- [Track master plan](../MASTER-PLAN.md) · [Progress tracker](../PROGRESS-TRACKER.md)
