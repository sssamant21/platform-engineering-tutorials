# OpenShift Administration — Master Plan

**Audience:** Platform Engineering / SRE / DBRE.  
**Target:** OCP 4.x, documentation reference 4.22.  
**Delivery:** 18 chapters × approximately 60 minutes. Hands-on labs use safe, isolated environments.  
**Prerequisite:** Familiarity with the [Kubernetes administration track](../kubernetes/README.md) or equivalent knowledge.

This track deliberately does not reproduce generic Kubernetes material. It teaches how Red Hat OpenShift installs, configures, observes, secures and maintains Kubernetes clusters using its own Operators, APIs, tools and lifecycle.

## Level 1 — Foundations and daily administration

| Chapter | Topic | Hands-on objective |
| --- | --- | --- |
| 001 | OCP architecture and administrator cluster health audit | Verify identity, version, Cluster Operators, nodes, MachineConfigPools and workload health |
| 002 | OpenShift CLI, web console, kubeconfig and access | Configure `oc`, contexts and read-only authorization checks safely |
| 003 | OCP control plane, RHCOS and CRI-O | Trace core control-plane and worker-node components |
| 004 | Cluster Operators, CVO and upgrade state | Interpret Available/Progressing/Degraded and version conditions |
| 005 | Machines, MachineSets and node operations | Diagnose Machine API and node problems; rehearse safe maintenance |
| 006 | Projects, pods, deployments and workload lifecycle | Create and verify disposable test workloads with least privilege |

## Level 2 — Enterprise operations

| Chapter | Topic | Hands-on objective |
| --- | --- | --- |
| 007 | Projects, quotas and multitenancy | Audit resource limits and namespace isolation |
| 008 | PV/PVC, StorageClasses, CSI and data safety | Validate provisioning, attachment and storage alerts |
| 009 | OVN-Kubernetes, Services, Routes and ingress | Trace DNS, service and ingress paths |
| 010 | Authentication, RBAC, SCC and service accounts | Verify effective permissions and security boundaries |
| 011 | OLM, add-on Operators and MachineConfig | Diagnose subscriptions, CSVs and configuration rollouts |
| 012 | Monitoring, logs, events and alerting | Build a read-only OCP health evidence bundle |

## Level 3 — Production engineering and recovery

| Chapter | Topic | Hands-on objective |
| --- | --- | --- |
| 013 | Capacity, resource pressure and autoscaling | Estimate headroom and diagnose scheduling pressure |
| 014 | Upgrade planning, gates and post-checks | Develop a version-specific change and rollback decision plan |
| 015 | etcd backups and platform/application recovery | Validate prerequisites, supported recovery paths and RPO/RTO assumptions |
| 016 | Incident response and cluster failure triage | Investigate Degraded Operators, NotReady nodes and unavailable routes |
| 017 | Stateful services on OCP | Explore Kafka/PostgreSQL/Redis availability, anti-affinity, PVC and disruption controls |
| 018 | Governance and production acceptance | Produce auditable runbooks, change reviews, evidence and operational ownership |

## Chapter acceptance gates

1. **Content QA:** verified Markdown links, command syntax, prerequisites and version scope.
2. **Lab QA:** isolated runtime or authorized read-only test with actual output recorded.
3. **Failure QA:** expected and failure conditions documented, including permission-denied cases.
4. **Safety QA:** no secrets, destructive examples fenced off, operational risk and recovery recorded.
5. **Approval:** independent technical review before calling any procedure production-ready.

Do not equate written tutorials or example output with actual test success.

## Source of truth

- [Red Hat OCP 4.22 documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22)
- [Cluster Operators](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/observability/operators/index)
- [Nodes](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/nodes/overview-of-nodes)
- [Troubleshooting](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/support/troubleshooting)
