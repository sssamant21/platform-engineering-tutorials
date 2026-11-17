# Chapter 016 — Incident Response and Cluster Failure Triage

**Audience:** OCP platform administrators, SREs and DBREs. **Duration:** ~60 minutes. **Baseline:** Red Hat OpenShift Container Platform 4.22. **Status:** Documentation draft; not cluster-tested.

## Outcomes and prerequisites
Identify an OCP incident's blast radius, preserve evidence, isolate API, ClusterOperator, node, network and workload symptoms, and establish escalation and recovery gates. Prerequisites: authorized `oc` access, known cluster identity, incident ticket, agreed severity/escalation contacts, and read-only permissions to inspect relevant resources. Cluster-wide `get` requires appropriately scoped authorization; namespace-only users should restrict queries to their projects. Kubernetes fundamentals: [existing track](../../kubernetes/README.md).

## 60-minute agenda
- 0–10 min: incident command, safety, severity and blast radius
- 10–25 min: control-plane and Operator health
- 25–40 min: nodes, MachineConfigPools, pods and routes
- 40–50 min: hypotheses, evidence and handoffs
- 50–60 min: tabletop decision gates and debrief

## First response: read-only only
Before commands, confirm cluster and context; do not display kubeconfig files or tokens.

```sh
oc whoami
oc config current-context
oc version
oc get clusterversion
oc get clusteroperators
oc get nodes -o wide
oc get machineconfigpools
```

**Interpretation:** ClusterOperators expose Available, Progressing and Degraded conditions; a Degraded condition is a symptom requiring message-level investigation, not permission to restart an Operator. An unreachable API means `oc` may not return anything; separate DNS/TCP/TLS/authentication errors before concluding etcd is down. A NotReady node is not necessarily a failed machine.

Investigate one affected Operator or node at a time:

```sh
oc describe clusteroperator <operator-name>
oc describe node <node-name>
oc get events -A --sort-by=.metadata.creationTimestamp
oc get pods -n <affected-namespace> -o wide
oc get events -n <affected-namespace> --sort-by=.metadata.creationTimestamp
oc get routes -n <affected-namespace>
oc get endpointslices -n <affected-namespace>
```

`oc get events -A` and node/Operator reads may be forbidden for project-scoped users; request a platform-admin evidence handoff instead of escalating privileges automatically. Events are transient and not an authoritative incident history. Do not export Secret resources, full environment variables, or unredacted diagnostics into tickets.

## Decision matrix
| Symptom | Read-only checks | Escalation |
| --- | --- | --- |
| API unavailable | Validate client context, DNS, network path, TLS error and whether multiple clients are affected | Platform incident commander and control-plane team; vendor support if persistent |
| ClusterOperator Degraded | `oc describe clusteroperator`; inspect related namespace pods/events if permitted | Owning platform Operator team |
| Node NotReady | `oc describe node`, node conditions, MCP and Machine/Node mapping when applicable | Compute/node team; DBRE for database pods |
| Route 503 | Route admission, Service selectors, EndpointSlices, pod readiness, ingress Operator | Networking/ingress and application owners |
| PVC pending or mount failure | PVC events, StorageClass, CSI Operator, node topology | Storage/CSI and DBRE; do not detach or delete |
| Stateful quorum risk | Identify primary/leader, replicas, PDB, PVC, replication health using approved application tools | DBRE/application owner before any node change |

## Change-control and recovery
No automatic drain, reboot, MachineConfig modification, Operator deletion, cluster upgrade, etcd restore or forced failover. Incident commander must document incident ID, target cluster, hypothesis, impact, authorization, maintenance/incident change approval, owners, success criteria, monitoring and stop conditions. For stateful systems obtain DBRE approval and verified recovery point; never treat an etcd snapshot as application database backup. An OCP upgrade cannot be assumed reversible; use the supported recovery procedure and Red Hat guidance for the exact installed version.

## Completion criteria
Produce a sanitized timeline, symptom-to-layer map, affected tenants, read-only evidence, competing hypotheses, escalation ownership and a documented go/no-go decision. See [Lab 016](../labs/016-incident-read-only-triage.md) and [Incident runbook](../runbooks/cluster-incident-response-triage.md).

## Official references
- [OCP 4.22 support and troubleshooting](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/support/troubleshooting)
- [OCP 4.22 nodes](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/nodes/overview-of-nodes)
- [OCP 4.22 documentation index](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22)

**Version gate:** Recheck command availability, role permissions and support procedures against the installed OCP release before operational use.
