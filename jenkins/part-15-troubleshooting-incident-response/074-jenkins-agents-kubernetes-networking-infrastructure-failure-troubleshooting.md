# Chapter 074 — Jenkins Agents, Kubernetes, Networking and Infrastructure Failure Troubleshooting

**Part 15 — Troubleshooting and Incident Response**  
**Audience:** Jenkins SRE, Kubernetes platform engineers, DevOps and on-call teams  
**Prerequisites:** Chapters 071–073, disposable Jenkins LTS, Kubernetes test cluster or VM agents, Prometheus/Grafana and approved access to agent logs/events.

## Objectives

Diagnose agent scheduling, provisioning, remoting, networking, DNS, TLS, cloud IAM, storage, resource pressure and Kubernetes infrastructure failures. Correlate Jenkins queue evidence with cluster and VM telemetry; restore agent service safely.

## 1. Agent lifecycle and fault domains

```text
Jenkins queue → cloud/agent template → Kubernetes API or VM provisioner
                                                |
                                  schedule → image pull → mount
                                                |
                                     agent JVM / remoting
                                                |
                                    executor → build → cleanup
```

Record timestamps for queue entry, provisioning request, pod creation, scheduling, image pull, agent ready and first build step. A job may remain queued despite free executors when labels or locks do not match.

## 2. First-response matrix

| Symptom | Likely domain | First evidence |
|---|---|---|
| No pod created | Jenkins cloud config, RBAC, quota | Controller logs |
| Pod Pending | scheduler, affinity, capacity, PVC | `describe pod` |
| ImagePullBackOff | registry, image digest, credentials | Pod events |
| Init/container fails | entrypoint, security context | Container logs |
| Agent offline | remoting, network, JVM, identity | Agent/controller logs |
| Agent OOMKilled | resource limits or workload | Pod last state |
| Pod evicted | node pressure | Events/node metrics |
| Workspace permission denied | UID/GID/PVC | Mount and security context |
| Intermittent DNS | CoreDNS/network policy | Resolver and cluster health |
| TLS handshake failure | CA, SNI, proxy | Certificate validation |
| Queue grows | labels, locks, executors, quota | Queue reason |

## 3. Kubernetes investigation commands

```sh
kubectl get pods -n jenkins-build -o wide
kubectl get events -n jenkins-build --sort-by=.lastTimestamp
kubectl describe pod <agent-pod> -n jenkins-build
kubectl logs -n jenkins-build <agent-pod> -c jnlp --previous
kubectl get nodes -o wide
kubectl describe node <node-name>
kubectl top pods -n jenkins-build
```

Replace placeholders and container names; the inbound agent container is not always named `jnlp`. Previous logs exist only after a restart, and `kubectl top` requires Metrics Server. Restrict diagnostic evidence because logs can contain secrets.

## 4. Scheduler and capacity

Check node selectors, affinities, taints/tolerations, topology spread, requests/limits, ResourceQuota, LimitRange, PVC topology and node allocatable resources. Inspect autoscaler/Karpenter logs and cloud instance limits. A cluster with free aggregate CPU can still lack a node matching an agent's constraints.

## 5. Image pulls and runtime

Inspect registry availability, image digest, service-account imagePullSecrets, rate limits, DNS, proxy and image size. Pin immutable digests for reproducibility. Verify entrypoint, Java/remoting compatibility and writable workspace. Do not use privileged containers or host Docker socket access as a generic workaround.

## 6. Agent remoting and identity

Diagnose agent handshake, Jenkins URL, WebSocket versus inbound TCP configuration, Java compatibility, TLS trust, agent secret scope, proxy and idle timeouts. Compare controller and agent timestamps. Rotate credentials through approved processes; never print inbound agent secrets in logs or tickets.

## 7. DNS and network policy

Use approved debug pods in an isolated namespace:

```sh
kubectl get networkpolicy -n jenkins-build
kubectl get svc,endpointslices -n jenkins
kubectl get pods -n kube-system -l k8s-app=kube-dns
```

Labels and resource names vary by cluster. Validate name resolution, service endpoint reachability, TLS chain, egress to SCM/artifact registries and firewall rules. Avoid disabling TLS verification or opening broad egress.

## 8. Storage and workspace

Check PVC Pending/binding, CSI driver events, mount failures, inode and disk capacity, filesystem ownership and concurrent workspace use. Do not delete shared workspaces, volumes or Jenkins home without retention/backup approval. Prefer ephemeral per-build workspaces for disposable agents.

## 9. VM/SSH agents

For non-Kubernetes agents inspect host reachability, SSH key/known-hosts, service account permissions, Java runtime, remoting logs, disk/inodes, CPU/memory, systemd/service status, proxy and firewall. Separate provisioning failure from remoting failure and build tool failures.

## 10. Capacity and reliability baseline

Measure:
- p95 agent request-to-ready latency.
- Pod Pending and image-pull duration.
- Agent online ratio and disconnect rate.
- Executor busy/available by compatible label.
- Kubernetes scheduling failure rate.
- Node memory/disk pressure and eviction counts.
- Build failures attributable to agent infrastructure.

Avoid raw pod names/build IDs as Prometheus metric labels. Correlate high-cardinality identifiers in logs/traces instead.

## 11. Failure scenarios

| # | Failure | Investigation |
|---|---|---|
| 01 | Cloud plugin cannot create pod | RBAC/cloud config |
| 02 | Service account lacks permission | `auth can-i` |
| 03 | Namespace quota exceeded | ResourceQuota |
| 04 | Node selector mismatch | Scheduling events |
| 05 | Missing toleration | Node taints |
| 06 | PVC unbound | PVC/CSI events |
| 07 | Registry auth denied | Pull events |
| 08 | Image digest missing | Registry manifest |
| 09 | Agent Java incompatible | Remoting logs |
| 10 | Agent secret invalid | Handshake |
| 11 | Jenkins URL unreachable | DNS/network |
| 12 | TLS certificate rejected | Trust chain |
| 13 | NetworkPolicy denies SCM | Egress rules |
| 14 | CoreDNS degraded | DNS telemetry |
| 15 | Agent OOMKilled | Container last state |
| 16 | Node disk pressure | Node conditions |
| 17 | Pod eviction | Events/pressure |
| 18 | Workspace permission denied | UID/GID/mount |
| 19 | Autoscaler cannot add nodes | Cloud quota |
| 20 | Agent disconnected mid-build | Remoting/network |

## 12. Six production runbooks

### A. Agent pods Pending
Confirm queue impact; inspect scheduler events, requests, affinity, taints, quotas and autoscaler; correct constraints or restore compatible capacity; validate request-to-ready p95.

### B. ImagePullBackOff
Inspect image reference/digest, registry credentials, DNS and rate limits; restore approved image or credential; rerun synthetic agent startup and checkout.

### C. Remoting disconnect
Inspect agent/controller logs, Java compatibility, Jenkins URL, WebSocket/TCP path, proxy idle timeout and TLS; correct endpoint/identity; verify stable agent connection and build.

### D. Network/DNS/TLS failure
Identify failing destination and protocol; validate DNS, endpoints, network policies and CA trust; restore narrowly scoped connectivity; confirm SCM/artifact access without bypassing TLS.

### E. OOMKilled/evicted agents
Check memory limits, node pressure and workload profile; adjust requests/limits or workload concurrency with approval; confirm no repeat under representative load.

### F. PVC/workspace incident
Inspect CSI/PVC binding, mount permissions and disk capacity; preserve artifacts; restore correct volume/ownership or ephemeral workspace; verify clean build.

## 13. Safe mitigation and recovery

1. Freeze risky template or cloud changes.
2. Preserve queue, pod events, logs and controller diagnostics.
3. Isolate affected agent pool and prevent cascading retries.
4. Fix least-privilege RBAC, scheduling, network or resource issue.
5. Roll back agent template/image by approved Git change if needed.
6. Verify agent startup, checkout, build and cleanup.
7. Measure queue and provisioning latency recovery.

## 14. Incident evidence template

```text
Incident ID / UTC start:
Jenkins core and cloud plugin versions:
Agent template and image digest:
Job label / queue reason:
Pod namespace/name / node:
Scheduling, pull, mount, readiness timestamps:
Pod status / events:
Agent remoting error:
Network/DNS/TLS evidence:
Quota / resource limits:
Mitigation and rollback:
Recovery p95 and representative build:
RCA/COA owner:
```

## 15. Acceptance criteria

- [ ] Queue reason and compatible pool identified.
- [ ] Pod lifecycle and scheduling evidence captured.
- [ ] Cloud RBAC and quotas validated.
- [ ] Image, Java and remoting compatibility checked.
- [ ] Network/DNS/TLS tested without insecure bypass.
- [ ] Storage/workspace permissions assessed.
- [ ] Failure domain isolated and corrected.
- [ ] Agent startup and representative build verified.
- [ ] Provisioning p95 and disconnect rate recovered.
- [ ] RCA/COA and owner sign-off documented.

**Companion:** [Chapter 074 hands-on lab](labs/074-jenkins-agents-kubernetes-networking-infrastructure-failure-troubleshooting-check.md).  
**Next:** Chapter 075 — Jenkins Enterprise Incident Response, Failure Simulation and Recovery Capstone.
