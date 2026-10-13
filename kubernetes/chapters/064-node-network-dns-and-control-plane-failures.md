# Chapter 064 — Node, Network, DNS and Control Plane Failures

**Track:** Kubernetes Administration · **Part 13 — Troubleshooting and Incident Response**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, platform engineers and Kubernetes administrators  
**Prerequisites:** Chapters 061–063; kubectl, Windows PowerShell; approved read-only access to a Kubernetes cluster; isolated staging namespace for optional diagnostics

## 1. Production scenario

A customer-facing API intermittently times out. Pods on one node fail readiness checks, DNS queries occasionally time out, and some Services have fewer Ready endpoints. Meanwhile, the API server responds slowly to `kubectl` requests. The incident could involve kubelet, CNI, CoreDNS, Service routing, an upstream dependency or the control plane.

**Goal:** isolate node, network, DNS and control-plane failure domains using time-correlated evidence, choose safe mitigation and verify customer recovery without disrupting stateful quorum or creating additional outages.

### Learning objectives

1. Distinguish node health, Pod networking, Service routing, DNS and API-server health.
2. Diagnose NotReady/Unknown nodes, kubelet and container runtime symptoms.
3. Investigate CNI, Pod IP, routing, NetworkPolicy, conntrack and MTU issues.
4. Trace DNS resolution through CoreDNS, Services and upstream resolvers.
5. Diagnose API-server latency, admission, etcd and controller-manager/scheduler symptoms.
6. Apply cloud-specific EKS/AKS checks without assuming node SSH or control-plane access.
7. Correlate logs, Events, metrics, traces and dependency evidence.
8. Build a safe production incident response runbook.

## 2. Failure-domain architecture

```text
Client
  |
Ingress / Load Balancer
  |
Service VIP / EndpointSlice
  |
Pod network (CNI, routing, policy)
  |
Application Pod on Node
  |                   |
Kubelet / CRI      CoreDNS -> upstream resolver
  |
Node OS / network / storage
  |
Kubernetes API server
  |         |          |
etcd    Scheduler   Controllers
```

A healthy API server does not prove DNS or workload networking is healthy. Likewise, a failing `kubectl` command may reflect client authentication, connectivity, API saturation or admission issues rather than an application outage.

## 3. Safety and evidence preservation

Default commands are read-only. Do not reboot, cordon, drain, restart CoreDNS, modify CNI, flush iptables/conntrack, alter cluster DNS or restart control-plane components without incident authorization and a validated rollback. For stateful workloads, check PDBs, quorum, volume attachment and data durability before node action.

```powershell
Get-Date -Format o
kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get events -A --sort-by=.lastTimestamp
kubectl get --raw /readyz
```

**Expected:** capture scope and timestamp. `/readyz` is an API-server readiness signal, not an end-to-end application SLI.

## 4. Lab 1 — Establish scope and identify affected failure domains

```powershell
kubectl get nodes -L topology.kubernetes.io/zone -o wide
kubectl get pods -A -o wide
kubectl get services -A
kubectl get endpointslices -A
kubectl get events -A --sort-by=.lastTimestamp
```

### Scope classification

| Pattern | Priority investigation |
|---|---|
| One Pod only | Container, probes, Service selector |
| All Pods on one node | Kubelet, CNI, node resources |
| One subnet/zone | Routing, cloud network, storage topology |
| One namespace | NetworkPolicy, DNS config, quota |
| Multiple namespaces | CoreDNS, CNI, ingress, cluster services |
| `kubectl` fails broadly | API server, authentication, network |
| Only external requests fail | Ingress, LB, DNS, firewall |
| Only database calls fail | DB, pool, routing, TLS, DNS |

**Expected:** an evidence-backed blast-radius statement, not a single assumed root cause.

## 5. Lab 2 — Diagnose NotReady and Unknown nodes

```powershell
kubectl get nodes -o wide
kubectl describe node REPLACE_WITH_NODE
kubectl get pods -A -o wide --field-selector spec.nodeName=REPLACE_WITH_NODE
kubectl get events -A --sort-by=.lastTimestamp
kubectl top nodes
```

### Node signals

| Condition | Interpretation |
|---|---|
| Ready=False | Kubelet reports node unhealthy/not ready |
| Ready=Unknown | Control plane has stopped receiving status |
| MemoryPressure | Node memory below configured threshold |
| DiskPressure | Filesystem or inode pressure |
| PIDPressure | PID exhaustion |
| NetworkUnavailable | May reflect CNI/network state; not uniformly set |

Check kubelet registration/certificates, runtime status, disk/inode pressure, node heartbeat, CNI readiness and cloud instance health. A node marked Unknown may be partitioned rather than powered off.

### Escalation

For EKS or AKS managed node pools, use approved cloud instance health, node logs and diagnostics. Do not assume direct SSH, host-level privileges or access to managed control-plane processes.

## 6. Lab 3 — Diagnose CNI and Pod networking

```powershell
kubectl -n kube-system get pods -o wide
kubectl -n kube-system get daemonsets
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get networkpolicies -A
kubectl get events -A --sort-by=.lastTimestamp
```

### Failure branches

- Pod sandbox creation fails: inspect CNI plugin health and kubelet Events.
- Pods receive no IP: inspect IPAM, subnet capacity and CNI configuration.
- Same-node traffic works but cross-node fails: investigate routing, overlay, security groups and MTU.
- Only selected Pods fail: investigate NetworkPolicy selectors and namespace labels.
- Intermittent connections fail: inspect conntrack saturation, NAT and node networking.
- Pod-to-Service fails but Pod-to-Pod works: inspect Service, EndpointSlices and service proxy/dataplane.

**Expected:** distinguish network dataplane problems from DNS resolution and application-level timeouts.

## 7. Lab 4 — Trace Service routing and EndpointSlices

```powershell
$ns = 'REPLACE_WITH_NAMESPACE'
$svc = 'REPLACE_WITH_SERVICE'
kubectl -n $ns get service $svc -o wide
kubectl -n $ns describe service $svc
kubectl -n $ns get endpointslices -l "kubernetes.io/service-name=$svc" -o wide
kubectl -n $ns get pods --show-labels -o wide
kubectl -n $ns get networkpolicies
```

### Service routing checks

1. Service selector matches intended Pods.
2. Pods are Ready and present in EndpointSlices.
3. `port`, `targetPort` and protocol match the application.
4. kube-proxy or eBPF dataplane is healthy, depending on cluster implementation.
5. NetworkPolicy allows intended traffic.
6. Ingress/LB target health is valid.

**Important:** kube-proxy may not be deployed in clusters using a replacement eBPF dataplane. Avoid assuming iptables rules exist on every platform.

## 8. Lab 5 — Diagnose CoreDNS and cluster DNS

```powershell
kubectl -n kube-system get deployment,service,pods -o wide
kubectl -n kube-system get configmap coredns
kubectl -n kube-system logs deployment/coredns --since=15m --tail=200
kubectl get pods -A -o wide
```

CoreDNS names and deployments may vary. Do not assume all clusters use the same Corefile or logging configuration.

### DNS investigation sequence

1. Determine whether failures affect internal Service names, external names or both.
2. Check Pod `dnsPolicy`, `dnsConfig` and resolver search paths.
3. Confirm the kube-dns Service IP and CoreDNS Ready endpoints.
4. Inspect CoreDNS restarts, saturation and error metrics.
5. Distinguish `NXDOMAIN`, `SERVFAIL`, timeout and stale cache.
6. Validate upstream resolver reachability for external names.
7. Check network policy, UDP/TCP 53 and node DNS behavior.
8. Correlate DNS failures with node/zone and traffic load.

### Common DNS patterns

| Symptom | Likely direction |
|---|---|
| Internal names fail everywhere | CoreDNS or cluster DNS Service |
| External names fail, internal work | Upstream DNS/egress |
| Only one namespace fails | DNS config or NetworkPolicy |
| Only one node fails | Node resolver/CNI/dataplane |
| Timeouts under load | CoreDNS capacity, conntrack, upstream |
| NXDOMAIN | Incorrect name/search domain or missing Service |

**Expected:** identify the failing DNS stage before scaling CoreDNS or changing upstream resolvers.

## 9. Lab 6 — Controlled staging DNS verification

**Approved staging only.** This diagnostic Pod uses a pinned example image tag and should be reviewed for image provenance before execution.

Save `ch064-dns.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch064
---
apiVersion: v1
kind: Pod
metadata:
  name: dns-debug
  namespace: ch064
spec:
  restartPolicy: Never
  containers:
    - name: toolbox
      image: busybox:1.36
      command: ["/bin/sh", "-c", "sleep 600"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
        limits:
          cpu: 100m
          memory: 64Mi
```

```powershell
kubectl apply -f .\ch064-dns.yaml
kubectl -n ch064 wait --for=condition=Ready pod/dns-debug --timeout=120s
kubectl -n ch064 exec dns-debug -- cat /etc/resolv.conf
kubectl -n ch064 exec dns-debug -- nslookup kubernetes.default.svc.cluster.local
kubectl -n ch064 exec dns-debug -- nslookup kubernetes.default
```

**Expected:** internal Kubernetes Service names resolve. If they do not, inspect the DNS Service and Pod network path. External DNS tests should be performed only where egress policy allows.

### Optional failure simulation

In a tabletop, model a NetworkPolicy that blocks DNS and predict expected behavior. Do not deploy broad deny policies into shared namespaces as a training exercise.

## 10. Lab 7 — Investigate API server and control-plane health

```powershell
kubectl get --raw /livez
kubectl get --raw /readyz
kubectl get --raw /version
kubectl get apiservices
kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations
kubectl get events -A --sort-by=.lastTimestamp
```

### Control-plane failure domains

| Component | Symptom | Evidence |
|---|---|---|
| API server | Requests slow/5xx/unavailable | API latency, readiness, logs |
| etcd | Slow writes, unavailable quorum | Backend metrics/logs, managed provider status |
| Scheduler | New Pods stay unscheduled | FailedScheduling Events, scheduler metrics |
| Controller manager | Desired state not reconciled | Controller errors, stale replicas |
| Admission webhooks | CREATE/UPDATE hangs or fails | Webhook latency/errors, configuration |
| API aggregation | Metrics or custom APIs fail | APIService conditions |
| Cloud controller | LB/node reconciliation issues | Cloud-controller logs/provider events |

**Important:** `/livez` and `/readyz` endpoints may be accessible only with appropriate RBAC or networking. Failure to access them can be an authorization/connectivity issue.

### Managed control-plane nuance

EKS/AKS control-plane logs and metrics are exposed through cloud-specific observability and support interfaces. Do not assume access to etcd hosts or control-plane static Pods.

## 11. Lab 8 — Investigate API latency and admission failures

Use an approved Prometheus endpoint if available.

### API server request latency

```promql
histogram_quantile(
  0.99,
  sum by (le, verb) (
    rate(apiserver_request_duration_seconds_bucket[5m])
  )
)
```

### API request error rates

```promql
sum by (code, verb) (
  rate(apiserver_request_total{code=~"5.."}[5m])
)
```

### Webhook investigation

```powershell
kubectl get validatingwebhookconfigurations
kubectl get mutatingwebhookconfigurations
kubectl get apiservices
kubectl get events -A --sort-by=.lastTimestamp
```

Check webhook Service endpoints, certificate validity, failure policy and timeout settings. **Do not disable a security admission webhook** as a generic mitigation; obtain security/platform approval and assess bypass consequences.

**Expected:** determine whether API slowness is due to request load, admission, storage backend, network or client authentication.

## 12. Lab 9 — EKS and AKS operational comparison

| Layer | EKS focus | AKS focus |
|---|---|---|
| Worker health | EC2, managed node groups, ASG, instance status | VMSS, node pools, instance health |
| Pod networking | VPC CNI, IP prefix/subnet capacity, security groups | Azure CNI/overlay, subnet/IP allocation, NSG |
| DNS | CoreDNS, VPC resolver | CoreDNS, Azure DNS/private DNS |
| Control plane | EKS control-plane logging/metrics | AKS diagnostic settings/control-plane logs |
| Load balancing | AWS Load Balancer Controller / cloud LB | Azure LB/Application Gateway integrations |
| Identity | IAM roles, node instance profile, workload identity | Managed identity, workload identity, Azure RBAC |

Do not assume the cluster uses the default CNI or load-balancer implementation. Verify installed components and cloud configuration.

## 13. Lab 10 — Multi-layer incident tabletop

**Scenario:** a Kubernetes API experiences 15% timeouts. One node becomes NotReady; DNS errors rise in one zone; a subset of Service EndpointSlices has fewer Ready addresses; API-server p99 also increases. A recent CNI upgrade and admission webhook rollout occurred within the same hour.

### Required investigation

1. Confirm customer impact, region/zone and affected request paths.
2. Compare failures by node, namespace, zone and Service.
3. Determine whether DNS fails only on affected nodes or cluster-wide.
4. Validate EndpointSlices, CNI health and node conditions.
5. Distinguish API latency from webhook latency and client-side timeouts.
6. Assess whether the CNI and webhook changes are causal or coincidental.
7. Preserve stateful quorum and avoid broad node drains.
8. Choose one controlled mitigation with approver and rollback.
9. Verify DNS, API responsiveness, Ready endpoints and customer SLIs.
10. Record independent contributing factors and monitoring gaps.

**Expected:** an evidence-based incident timeline with at least two competing hypotheses and explicit verification criteria.

## 14. Production troubleshooting decision tree

```text
Is customer traffic failing?
  |
  +-- Only one Pod? -> application, probes, container
  |
  +-- All Pods on one node? -> kubelet, CNI, runtime, pressure
  |
  +-- Service name fails to resolve? -> CoreDNS, DNS config, policy
  |
  +-- DNS works but Service fails? -> EndpointSlices, ports, dataplane
  |
  +-- Pod-to-Pod fails? -> CNI, routing, policy, MTU
  |
  +-- Only ingress fails? -> LB, ingress, TLS, external DNS
  |
  +-- kubectl/API also slow? -> API, webhook, etcd, auth, network
  |
  +-- External dependency only? -> upstream DNS, egress, DB, firewall
```

Test each branch with independent evidence; multiple layers can fail simultaneously.

## 15. Production incident response runbook

### Detect and scope

1. Confirm service SLO impact, error rate, latency and incident window.
2. Classify by node, zone, namespace, Service and client network.
3. Identify recent node pool, CNI, DNS, ingress and admission changes.

### Diagnose

1. Capture node conditions and workload placement.
2. Inspect CNI, Pod IP allocation and EndpointSlices.
3. Check CoreDNS, resolver behavior and upstream connectivity.
4. Evaluate API readiness, admission and control-plane latency.
5. Correlate logs, Events, metrics and traces.

### Mitigate

1. Select a reversible, low-blast-radius action with owner and rollback.
2. Do not bypass security policies or disrupt database quorum without approval.
3. Preserve monitoring access and evidence.
4. Verify affected paths end-to-end after remediation.

### Close

Document customer impact, exact failure layer, causal evidence, telemetry gaps, follow-up ownership and regression tests.

## 16. Prevention controls

- Monitor node Ready/Unknown and pressure conditions by zone.
- Alert on CNI Pod failures, IP exhaustion and network errors.
- Monitor CoreDNS latency, errors, saturation and upstream availability.
- Monitor EndpointSlice readiness and ingress backend health.
- Track API-server request latency and admission webhook errors.
- Use staged node pool/CNI upgrades with rollback plans.
- Test DNS and Service routing during release acceptance.
- Validate control-plane dependency and admission failure behavior.
- Maintain capacity headroom and protect stateful quorum.
- Define cloud-provider escalation paths and diagnostic access.

## 17. Evidence template

```text
Incident ID:
Cluster / region / zone:
Time window (UTC):
Customer impact / SLIs:
Affected Services / namespaces:
Affected nodes / node conditions:
Pod IP / CNI health:
EndpointSlice and ingress state:
CoreDNS / upstream DNS findings:
NetworkPolicy / routing findings:
API readiness / latency:
Admission webhook findings:
Cloud provider events:
Recent changes:
Confirmed observations:
Hypotheses and contradictions:
Mitigation / approver / rollback:
Recovery verification:
Follow-up owners:
```

## 18. Acceptance checklist

- [ ] Failure domain scoped by node, zone, namespace and Service.
- [ ] Node Ready/Unknown and pressure signals interpreted.
- [ ] CNI, Pod IP and cross-node routing branches reviewed.
- [ ] Service selector, ports and EndpointSlices verified.
- [ ] CoreDNS and upstream DNS paths distinguished.
- [ ] Isolated DNS lab completed or marked not run.
- [ ] API server, admission, scheduler and controller symptoms reviewed.
- [ ] EKS/AKS managed control-plane access constraints documented.
- [ ] Metrics, logs, Events and traces correlated.
- [ ] Multi-layer incident tabletop completed.
- [ ] Safe mitigation, rollback and recovery SLIs defined.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

## 19. Cleanup

Only remove the isolated staging namespace after collecting approved evidence:

```powershell
kubectl -n ch064 get pods
kubectl delete namespace ch064
```

Do not delete existing CoreDNS, CNI, kube-system or production resources.

**Status:** Draft — runtime validation and technical review pending.

## 20. References

- [Kubernetes Cluster Troubleshooting](https://kubernetes.io/docs/tasks/debug/debug-cluster/)
- [Debug Services](https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/)
- [DNS Debugging](https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/)
- [DNS for Services and Pods](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)
- [Service](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Node Status](https://kubernetes.io/docs/reference/node/node-status/)
- [Kubernetes API Health Endpoints](https://kubernetes.io/docs/reference/using-api/health-checks/)

**Next:** Chapter 065 — Production Incident Investigation Project (Part 13 capstone).
