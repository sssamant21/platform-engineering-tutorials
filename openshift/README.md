# Red Hat OpenShift Container Platform (OCP) Administration

**Enterprise Learning Path for Platform Engineers, SREs and DBREs**

A dedicated, hands-on OpenShift administration track alongside [Kubernetes Administration](../kubernetes/README.md). Kubernetes concepts are prerequisites; these lessons focus on Red Hat OpenShift operational differences and production administration.

- **Scope:** OpenShift Container Platform 4.x, with Red Hat OCP 4.22 documentation as the initial reference baseline.
- **Format:** 18 chapters, designed for approximately 60 minutes each, with lab work, diagnostics, and evidence.
- **Audience:** Beginner-to-advanced platform administrators, SREs, and DBREs supporting stateful workloads.
- **Policy:** No commands are certified for the reader's production cluster without version-specific review and environment validation.

## Start here

1. [Master plan — all 18 chapters](MASTER-PLAN.md)
2. [Progress and validation tracker](PROGRESS-TRACKER.md)
3. [Chapter 012 — Monitoring, logs, events and alerting](chapters/012-monitoring-logging-events-and-alerting.md)
4. [Lab 012 — Read-only observability evidence](labs/012-observability-read-only-evidence.md)
5. [Runbook — Monitoring, alerts and logging triage](runbooks/monitoring-alert-logging-triage.md)
6. [Chapter 011 — OLM, add-on Operators and MachineConfig](chapters/011-olm-addon-operators-and-machineconfig.md)
7. [Lab 011 — Read-only OLM and MCP audit](labs/011-olm-machineconfig-read-only-audit.md)
8. [Runbook — OLM and MachineConfig triage](runbooks/olm-machineconfig-triage.md)
9. [Chapter 010 — Authentication, RBAC, SCC and ServiceAccounts](chapters/010-authentication-rbac-scc-and-serviceaccounts.md)
10. [Lab 010 — Read-only security and access audit](labs/010-security-rbac-scc-read-only-audit.md)
11. [Runbook — RBAC, SCC and ServiceAccount access triage](runbooks/rbac-scc-serviceaccount-access-triage.md)
12. [Chapter 009 — OVN-Kubernetes, Services, Routes, DNS and ingress](chapters/009-ovn-kubernetes-services-routes-and-ingress.md)
13. [Lab 009 — Read-only Service and Route audit](labs/009-network-service-route-read-only-audit.md)
14. [Runbook — Network, Route, DNS and ingress triage](runbooks/ovn-service-route-dns-ingress-triage.md)
15. [Chapter 008 — Persistent storage, PV/PVC, StorageClass and CSI](chapters/008-persistent-storage-pv-pvc-storageclass-and-csi.md)
16. [Lab 008 — Read-only storage audit](labs/008-persistent-storage-read-only-audit.md)
17. [Runbook — PVC and CSI storage triage](runbooks/pvc-csi-storage-triage.md)
18. [Chapter 007 — Projects, ResourceQuotas, LimitRanges and multitenancy](chapters/007-projects-quotas-limitranges-and-multitenancy.md)
19. [Lab 007 — Project quota and LimitRange audit](labs/007-project-quota-and-limitrange-audit.md)
20. [Runbook — Project quota and LimitRange triage](runbooks/project-quota-limitrange-triage.md)
21. [Chapter 006 — Projects, pods, deployments and workload lifecycle](chapters/006-projects-pods-deployments-and-workload-lifecycle.md)
22. [Lab 006 — Disposable deployment lifecycle](labs/006-disposable-deployment-lifecycle.md)
23. [Runbook — Deployment and pod triage](runbooks/workload-deployment-triage.md)
24. [Chapter 005 — Machine API, MachineSets and safe node operations](chapters/005-machine-api-machinesets-and-node-operations.md)
25. [Lab 005 — Machine and node inventory](labs/005-machine-api-node-inventory.md)
26. [Runbook — Machine API and node triage](runbooks/machine-api-node-triage.md)
27. [Chapter 004 — Cluster Operators, CVO and update state](chapters/004-cluster-operators-cvo-and-update-state.md)
28. [Lab 004 — CVO and Cluster Operator read-only audit](labs/004-clusteroperator-cvo-read-only-audit.md)
29. [Runbook — Cluster Operator / CVO degraded triage](runbooks/clusteroperator-cvo-degraded-triage.md)
30. [Chapter 003 — Control plane, RHCOS, CRI-O and nodes](chapters/003-ocp-control-plane-rhcos-crio-and-nodes.md)
31. [Lab 003 — Control-plane and node inventory](labs/003-control-plane-rhcos-crio-node-inventory.md)
32. [Runbook — Node runtime and MachineConfigPool triage](runbooks/node-runtime-and-machineconfigpool-triage.md)
33. [Chapter 002 — CLI, console, kubeconfig and RBAC](chapters/002-ocp-cli-console-and-access.md)
34. [Lab 002 — Context and RBAC verification](labs/002-oc-cli-context-and-rbac.md)
35. [Runbook — CLI login, context and RBAC triage](runbooks/cli-login-context-rbac-triage.md)
36. [Chapter 001 — OCP architecture and first cluster health audit](chapters/001-ocp-architecture-and-cluster-health.md)
37. [Lab 001 — Read-only cluster health audit](labs/001-read-only-cluster-health-audit.md)
38. [Runbook — Cluster health triage](runbooks/cluster-health-triage.md)

## Repository conventions

- `chapters/` — canonical numbered tutorials
- `labs/` — runnable exercises with validation and evidence criteria
- `runbooks/` — operational diagnosis, escalation and recovery procedures
- `scripts/` — future audited helpers (not required for the first lab)
- `MASTER-PLAN.md` — syllabus and learning sequence
- `PROGRESS-TRACKER.md` — drafting, testing and approval status

## Operational safety standards

- Read-only commands may be used with authorization; modifications require an approved change, prechecks and rollback plan.
- Always confirm active kubeconfig context, cluster identity, privileges and target namespace before commands.
- Never print, commit or paste kubeconfig credentials, bearer tokens, passwords or Secrets.
- Use non-production environments for disruption, drain, scaling, upgrades and restore exercises.
- Record actual lab output separately from examples; never mark a runtime test passed without execution evidence.
- Review the exact OCP minor version, topology and supported configuration against Red Hat documentation.

## References

- [Red Hat OpenShift Container Platform 4.22 documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22)
- [Red Hat Cluster Operators reference](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/observability/operators/index)
- [Red Hat OpenShift troubleshooting](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/support/troubleshooting)
