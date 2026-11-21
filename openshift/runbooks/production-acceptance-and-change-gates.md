# Runbook — Production Acceptance and Change Gates

**Status:** Draft; requires independent review and cluster-specific approval. **Baseline:** OCP 4.22 reference, verify deployed version. **Use:** onboarding, change review, audit, or readiness triage.

## Trigger and authority

Use for new cluster/service acceptance, material configuration change, upgrade, recovery drill, or unresolved operational ownership. Incident commander owns urgent coordination; change authority approves production modifications; platform admin executes approved platform changes; DBRE/data owner controls database recovery and data integrity acceptance.

## 1. Identify scope safely

Confirm `oc config current-context`, `oc whoami`, and authorized read permissions (`oc auth can-i get clusteroperators.config.openshift.io`). If approved, inspect `oc get clusterversion`, `oc get clusteroperators`, `oc get nodes`, `oc get mcp`. Compare with prior evidence and business SLO. Do not collect Secrets or raw kubeconfig. For isolated tenants, request namespace-only read permissions.

## 2. Classify gaps

- **BLOCK:** unknown production owner, unsupported upgrade path, absent change approval, unverified backups for a recovery operation, unresolved split-brain/fencing risk, active critical incident, or absent service validation owner.
- **CONDITIONAL:** noncritical documentation or monitoring gaps with named owner, deadline and written risk acceptance.
- **PASS:** all required acceptance evidence reviewed and signed by independent owners.

Missing evidence is not a PASS. For databases, validate native replication, backup and consistency independently of Kubernetes pod readiness and PVC state.

## 3. Change go/no-go

Before any write: require ticket, version-specific supported procedure, impact map, named implementer and approver, communication plan, approved window, baseline, stop thresholds, recovery options, and service-specific verification. Confirm rollback feasibility; for OCP upgrades, etcd recovery, data migration and failover, prefer vendor-supported **forward recovery** when simple rollback is unsupported. Obtain platform, security, app and DBRE signoff as relevant.

## 4. Escalation

Escalate API/ClusterOperator/MCP issues to platform on-call; storage/network to owning infrastructure team; RBAC/SCC to security; PostgreSQL/Kafka/MongoDB/Redis consistency or failover to DBRE and application owner. Engage Red Hat Support for platform recovery or unclear vendor-supported remediation. `oc adm must-gather` is a diagnostic collection operation that may consume resources and capture sensitive data; run only with authorized elevated access and approved evidence handling, following the version-specific support guide.

## 5. Closure and acceptance

Record sanitized before/after evidence, exact deployed version, change/incident ID, test results, unresolved risks, named independent reviewer and date. If post-change SLO, cluster health, storage consistency or application checks fail, stop further change and invoke the approved incident/recovery decision tree. Do not declare production readiness until runtime testing, security review and owner approvals are complete.

## References

- [Chapter 018](../chapters/018-enterprise-governance-and-production-acceptance.md)
- [Lab 018](../labs/018-governance-production-acceptance-read-only-audit.md)
- [Red Hat OCP 4.22 Support](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html-single/support/index)
- [Red Hat OCP 4.22 documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22)
