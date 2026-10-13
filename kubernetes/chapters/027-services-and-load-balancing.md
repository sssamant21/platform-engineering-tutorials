# Chapter 027 — Services and Load Balancing

**Track:** Kubernetes Administration · **Part 06 — Kubernetes Networking**  
**Status:** Draft — hands-on execution and technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators and platform engineers  
**Prerequisites:** Chapters 026 (networking and CNI), 016–019 (Pods and workloads); Docker Desktop, kind, kubectl, Windows PowerShell

## 1. Production scenario and objectives

A web application has three healthy Pods, but traffic to its Service fails intermittently. During a rollout, some requests time out; the application team assumes Kubernetes automatically balances every connection equally. An external LoadBalancer remains Pending on a local cluster, and another Service has no backends despite Pods being Ready.

This chapter separates **Service discovery**, **backend eligibility**, **traffic forwarding**, and **external load-balancer provisioning**.

After completing it, you can:

1. Explain ClusterIP, NodePort, LoadBalancer, ExternalName and headless Services.
2. Trace Service selectors, EndpointSlices, readiness and targetPort resolution.
3. Understand Service forwarding via kube-proxy (iptables/IPVS/nftables where applicable) or eBPF alternatives.
4. Distinguish connection-level distribution from request-level balancing and session affinity.
5. Explain externalTrafficPolicy, internalTrafficPolicy, source-IP preservation and traffic distribution hints.
6. Investigate dual-stack, DNS, port mapping, cloud integrations and common failures.
7. Perform seven practical labs, collect evidence and validate safe recovery.

## 2. Mental model

```text
                  Client Pod
                     |
            DNS: api.ch027.svc
                     |
             Service ClusterIP
                     |
         Service datapath (varies)
                     |
               EndpointSlice
           +---------+---------+
           |         |         |
       Pod A:80   Pod B:80   Pod C:80
        Ready      Ready      Ready

 External client -> cloud LB / gateway -> node or Pod
                                       -> Service backends
```

A Service is an API abstraction with stable identity. Its **ClusterIP is not normally an application process** listening on an interface. The datapath implements forwarding to eligible endpoints. Some implementations bypass kube-proxy entirely.

**Critical distinction:** DNS answers, Service objects, EndpointSlices, packet forwarding and application health are separate layers. Each can fail independently.

## 3. Service types and use cases

| Type | Exposure | Typical use | Important caveat |
|---|---|---|---|
| ClusterIP | Cluster-internal virtual IP | API, cache, database frontend | Default type; not an external listener |
| NodePort | Node IP plus allocated/static port | Basic external entry, LB backend | Firewall and node routing required |
| LoadBalancer | Provider/integration-provisioned external or internal LB | Cloud-facing TCP/UDP services | Requires controller/provider; may remain Pending locally |
| ExternalName | DNS CNAME-like mapping | DNS alias to external hostname | No normal Pod endpoints or Service proxying |
| Headless (`clusterIP: None`) | DNS directly returns endpoint addresses | StatefulSet peer discovery | No ClusterIP virtual forwarding |

An Ingress or Gateway is a separate API/controller abstraction for application routing, TLS and other layer-7 behavior. It does not replace the underlying need for reachable endpoints.

### Type ClusterIP

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api
spec:
  type: ClusterIP
  selector:
    app: api
  ports:
    - name: http
      protocol: TCP
      port: 80
      targetPort: http
```

### Type NodePort

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api-nodeport
spec:
  type: NodePort
  selector:
    app: api
  ports:
    - name: http
      port: 80
      targetPort: http
      nodePort: 30080
```

A fixed NodePort must be available and within the cluster's configured NodePort range (often 30000–32767, but configurable). In production, prefer an approved edge architecture and avoid opening every node broadly.

### Type LoadBalancer

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api-public
spec:
  type: LoadBalancer
  selector:
    app: api
  ports:
    - port: 80
      targetPort: http
```

The Service does **not** guarantee a public address. Cloud provider controllers, load-balancer integrations, permissions, subnet selection and quotas determine provisioning. Local kind usually lacks a cloud load-balancer controller; `EXTERNAL-IP: <pending>` can be expected.

### ExternalName and headless

```yaml
apiVersion: v1
kind: Service
metadata:
  name: external-docs
spec:
  type: ExternalName
  externalName: docs.example.org
---
apiVersion: v1
kind: Service
metadata:
  name: db-peers
spec:
  clusterIP: None
  selector:
    app: database
  ports:
    - port: 5432
```

An ExternalName is a DNS alias, not an HTTP redirect, TLS termination, or a TCP proxy. Application TLS/SNI/Host handling may need explicit configuration. Headless Services are especially useful for StatefulSets, but clients must handle returned endpoint addresses and changes.

## 4. Ports: port, targetPort, nodePort and containerPort

```text
Client -> Service port: 80 -> Pod targetPort: 8080
                  |
             NodePort: 30080 (if configured)
```

- `port`: Service-facing port.
- `targetPort`: backend container port number or named port; defaults to Service `port` if omitted.
- `nodePort`: node-exposed port for NodePort and certain LoadBalancer configurations.
- `containerPort`: Pod metadata/documentation; declaring it does not make the application listen.

Named `targetPort` is resolved against the port names of selected Pods. A mismatch can produce unusable backend port information even when labels match.

## 5. Selectors, EndpointSlices and readiness

The EndpointSlice controller generally creates and updates EndpointSlices for selector-based Services. Readiness and terminating state affect endpoint conditions; the exact traffic behavior also depends on Service traffic policies and datapath implementation.

```powershell
kubectl -n NAMESPACE get service api -o yaml
kubectl -n NAMESPACE get pods -l app=api -o wide
kubectl -n NAMESPACE get endpointslices -l kubernetes.io/service-name=api -o yaml
```

Check `conditions.ready`, `conditions.serving` and `conditions.terminating` when present. During graceful termination, a terminating endpoint can still be serving; do not equate every terminating endpoint with immediate packet rejection. Legacy Endpoints may be incomplete or truncated at scale; prefer EndpointSlices.

### Selectorless Services

A Service can have no selector and use manually managed EndpointSlices. This is an advanced integration pattern; EndpointSlices must be managed explicitly and must not be confused with automatically generated slices. Kubernetes API-server proxy behavior has restrictions for endpoints not mapped to Pods.

## 6. How Service traffic is balanced

Kubernetes Services do not promise strict round-robin distribution of individual HTTP requests. The datapath often chooses a backend for a **connection** or flow. HTTP keep-alive, HTTP/2 multiplexing, conntrack, topology and session affinity can cause repeated requests to reach one backend.

- **kube-proxy:** Depending on version/configuration, may program iptables, IPVS or nftables rules.
- **eBPF datapath:** May implement Service translation and policy without kube-proxy.
- **conntrack:** Flow state can preserve existing backend mappings after endpoint changes.
- **ClientIP session affinity:** Can pin a client source IP to a backend for a configured timeout; behavior is implementation- and traffic-path-dependent.
- **Traffic distribution preferences:** PreferSameZone or related hints may influence eligible backends, subject to cluster support and traffic policies. They are not strict cross-zone isolation.

Never infer equal backend request counts from a few `curl` commands.

## 7. Traffic policies and source IP

### externalTrafficPolicy

- `Cluster`: external traffic may be forwarded to backends on other nodes; client source IP may be altered depending on the datapath.
- `Local`: directs externally arriving traffic to local node endpoints, commonly to preserve client source IP and avoid a second hop. Nodes without eligible local endpoints may not serve that traffic; load-balancer health checks and node selection matter.

### internalTrafficPolicy

- `Cluster`: internal traffic can reach cluster-wide eligible endpoints.
- `Local`: internal traffic is restricted to node-local endpoints. If no eligible local endpoint exists, traffic may be dropped even when healthy endpoints exist elsewhere.

**Operational warning:** These settings are not general performance toggles. They alter reachability, failover and capacity requirements. Test them with node loss and rolling updates.

### LoadBalancer specifics

Some implementations allocate NodePorts by default for LoadBalancer Services, while configurations such as `allocateLoadBalancerNodePorts: false` are supported for datapaths that route directly to Pods. Do not assume every cloud LB traverses NodePort. Cloud-specific annotations and loadBalancerClass should be verified against the installed controller.

## 8. DNS, IP families and protocol

Typical in-cluster name:

```text
api.ch027.svc.cluster.local
```

The actual cluster DNS suffix may differ. Service DNS records and search domains depend on Pod DNS policy and CoreDNS configuration.

Dual-stack clusters can allocate IPv4 and IPv6 Service addresses according to `ipFamilyPolicy` and `ipFamilies`. The CNI, nodes, Service datapath and external LB must support the intended IP families. Do not assume that an IPv6 address exists in a default kind lab.

Kubernetes Services support TCP, UDP and SCTP subject to platform and CNI support. Application protocols (HTTP, gRPC, database wire protocols) may have their own connection pooling and health-check behaviors.

## 9. Hands-on lab setup

Use only a **disposable kind cluster**. Windows PowerShell commands below use explicit `--context` for every kubectl operation.

```powershell
docker version
kind version
kubectl version --client
New-Item -ItemType Directory -Force .\k8s-ch027 | Out-Null
Set-Location .\k8s-ch027
@'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
'@ | Set-Content -Encoding ascii .\kind-config.yaml
kind create cluster --name k8s-admin-ch027 --config .\kind-config.yaml --wait 180s
kubectl config current-context
kubectl --context kind-k8s-admin-ch027 get nodes -o wide
kubectl --context kind-k8s-admin-ch027 create namespace ch027
```

**Stop conditions:** wrong context, shared cluster, missing Docker capacity, nodes not Ready, or image pull failures. Do not continue by switching to production.

## 10. Lab A — Deploy a healthy backend and ClusterIP Service

Use a Deployment with three replicas and a Service. A lightweight Python HTTP server prints the Pod hostname to make endpoint selection observable.

```powershell
@'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo
  namespace: ch027
spec:
  replicas: 3
  selector:
    matchLabels:
      app: echo
  template:
    metadata:
      labels:
        app: echo
    spec:
      containers:
        - name: server
          image: python:3.12-alpine
          command:
            - python
            - -u
            - -c
            - |
              from http.server import BaseHTTPRequestHandler, HTTPServer
              import os
              class Handler(BaseHTTPRequestHandler):
                  def do_GET(self):
                      body = (os.environ["HOSTNAME"] + "\n").encode()
                      self.send_response(200)
                      self.send_header("Content-Type", "text/plain")
                      self.send_header("Content-Length", str(len(body)))
                      self.end_headers()
                      self.wfile.write(body)
              HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
          ports:
            - name: http
              containerPort: 8080
          readinessProbe:
            httpGet:
              path: /
              port: http
            initialDelaySeconds: 2
            periodSeconds: 3
          resources:
            requests:
              cpu: 25m
              memory: 32Mi
            limits:
              memory: 128Mi
---
apiVersion: v1
kind: Service
metadata:
  name: echo
  namespace: ch027
spec:
  type: ClusterIP
  selector:
    app: echo
  ports:
    - name: http
      port: 80
      targetPort: http
'@ | Set-Content -Encoding utf8 .\echo.yaml
kubectl --context kind-k8s-admin-ch027 apply --dry-run=server -f .\echo.yaml
kubectl --context kind-k8s-admin-ch027 apply -f .\echo.yaml
kubectl --context kind-k8s-admin-ch027 -n ch027 rollout status deployment/echo --timeout=180s
kubectl --context kind-k8s-admin-ch027 -n ch027 get deployment,pods,service -o wide
kubectl --context kind-k8s-admin-ch027 -n ch027 get endpointslices -l kubernetes.io/service-name=echo -o wide
```

**Expected:** Deployment 3/3 Ready; Service ClusterIP allocated; EndpointSlices list three ready backend Pod addresses.

## 11. Lab B — DNS and Service request distribution

Create a client:

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: ch027
spec:
  containers:
    - name: toolbox
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\client.yaml
kubectl --context kind-k8s-admin-ch027 apply -f .\client.yaml
kubectl --context kind-k8s-admin-ch027 -n ch027 wait --for=condition=Ready pod/client --timeout=180s
kubectl --context kind-k8s-admin-ch027 -n ch027 exec client -- nslookup echo.ch027.svc.cluster.local
kubectl --context kind-k8s-admin-ch027 -n ch027 exec client -- sh -c 'for i in 1 2 3 4 5 6 7 8 9 10; do wget -qO- http://echo.ch027.svc.cluster.local/; done'
```

**Expected:** DNS resolves the ClusterIP; HTTP returns Pod hostnames. The sample may not be evenly distributed across replicas. Do not use ten requests to prove fairness.

Capture Service configuration and backend readiness:

```powershell
kubectl --context kind-k8s-admin-ch027 -n ch027 describe service echo
kubectl --context kind-k8s-admin-ch027 -n ch027 get endpointslices -l kubernetes.io/service-name=echo -o yaml
```

## 12. Lab C — Service selector failure and recovery

Inject a selector that matches no Pods:

```powershell
kubectl --context kind-k8s-admin-ch027 -n ch027 patch service echo --type=merge -p '{"spec":{"selector":{"app":"missing"}}}'
kubectl --context kind-k8s-admin-ch027 -n ch027 get endpointslices -l kubernetes.io/service-name=echo -o wide
kubectl --context kind-k8s-admin-ch027 -n ch027 exec client -- wget -T 3 -qO- http://echo.ch027.svc.cluster.local/
```

**Expected:** zero eligible backends and failed Service HTTP. A DNS answer may still resolve correctly, proving that DNS success does not imply Service health.

Restore:

```powershell
kubectl --context kind-k8s-admin-ch027 -n ch027 patch service echo --type=merge -p '{"spec":{"selector":{"app":"echo"}}}'
kubectl --context kind-k8s-admin-ch027 -n ch027 get endpointslices -l kubernetes.io/service-name=echo
kubectl --context kind-k8s-admin-ch027 -n ch027 exec client -- wget -qO- http://echo.ch027.svc.cluster.local/
```

**Expected:** three ready endpoints return after controller reconciliation; HTTP succeeds.

## 13. Lab D — Readiness controls backend eligibility

Scale the Deployment down to two replicas and back up:

```powershell
kubectl --context kind-k8s-admin-ch027 -n ch027 scale deployment/echo --replicas=2
kubectl --context kind-k8s-admin-ch027 -n ch027 rollout status deployment/echo --timeout=180s
kubectl --context kind-k8s-admin-ch027 -n ch027 get endpointslices -l kubernetes.io/service-name=echo -o yaml
kubectl --context kind-k8s-admin-ch027 -n ch027 scale deployment/echo --replicas=3
kubectl --context kind-k8s-admin-ch027 -n ch027 rollout status deployment/echo --timeout=180s
kubectl --context kind-k8s-admin-ch027 -n ch027 get endpointslices -l kubernetes.io/service-name=echo -o yaml
```

**Expected:** EndpointSlice membership reflects Pod readiness and scaling. During termination, endpoint conditions may show `terminating` and `serving`; record actual values rather than assuming immediate disappearance.

For a deterministic readiness-negative test, create a separate Pod with a deliberately failing readiness probe and the same Service selector:

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: unready
  namespace: ch027
  labels:
    app: echo
spec:
  containers:
    - name: nginx
      image: nginx:stable
      readinessProbe:
        httpGet:
          path: /does-not-exist
          port: 80
        periodSeconds: 3
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\unready.yaml
kubectl --context kind-k8s-admin-ch027 apply -f .\unready.yaml
kubectl --context kind-k8s-admin-ch027 -n ch027 get pod unready
kubectl --context kind-k8s-admin-ch027 -n ch027 get endpointslices -l kubernetes.io/service-name=echo -o yaml
```

**Expected:** the Pod is Running but not Ready; its endpoint is not eligible for ordinary Service traffic. Its endpoint may appear with `ready: false`. Remove it:

```powershell
kubectl --context kind-k8s-admin-ch027 -n ch027 delete pod unready
```

## 14. Lab E — NodePort and local exposure

Create a NodePort Service:

```powershell
@'
apiVersion: v1
kind: Service
metadata:
  name: echo-nodeport
  namespace: ch027
spec:
  type: NodePort
  selector:
    app: echo
  ports:
    - name: http
      port: 80
      targetPort: http
      nodePort: 30080
'@ | Set-Content -Encoding ascii .\nodeport.yaml
kubectl --context kind-k8s-admin-ch027 apply -f .\nodeport.yaml
kubectl --context kind-k8s-admin-ch027 -n ch027 get service echo-nodeport
```

**Expected:** NodePort 30080 allocated, assuming the port is in the configured range and unused.

**Kind/Docker Desktop caveat:** NodePort is exposed on kind node containers, not automatically on your Windows host. A browser request to `localhost:30080` may fail unless the kind cluster was created with a matching `extraPortMappings` configuration. This is not proof of Service failure.

Use a client Pod and node IP to test the node-facing datapath:

```powershell
$nodeIp = kubectl --context kind-k8s-admin-ch027 get node k8s-admin-ch027-worker -o jsonpath='{.status.addresses[?(@.type=="InternalIP")].address}'
kubectl --context kind-k8s-admin-ch027 -n ch027 exec client -- wget -T 5 -qO- "http://$($nodeIp):30080/"
```

**Expected in typical kind networking:** HTTP returns a backend hostname. If the Pod cannot reach the node IP due to runtime networking restrictions, record the limitation and verify Service objects/ports; do not change the host firewall to force the lab to pass.

## 15. Lab F — Headless Service and direct endpoint discovery

```powershell
@'
apiVersion: v1
kind: Service
metadata:
  name: echo-headless
  namespace: ch027
spec:
  clusterIP: None
  selector:
    app: echo
  ports:
    - name: http
      port: 8080
      targetPort: http
'@ | Set-Content -Encoding ascii .\headless.yaml
kubectl --context kind-k8s-admin-ch027 apply -f .\headless.yaml
kubectl --context kind-k8s-admin-ch027 -n ch027 get service echo-headless -o wide
kubectl --context kind-k8s-admin-ch027 -n ch027 exec client -- nslookup echo-headless.ch027.svc.cluster.local
kubectl --context kind-k8s-admin-ch027 -n ch027 get endpointslices -l kubernetes.io/service-name=echo-headless
```

**Expected:** `CLUSTER-IP: None`; DNS returns backend Pod addresses rather than a virtual ClusterIP. Exact answer ordering and count depend on DNS cache, endpoint readiness and query timing.

**Stateful workload caution:** A headless Service supports direct peer discovery but does not automatically guarantee ordered startup, quorum, stable storage, or failover.

## 16. Lab G — LoadBalancer and ExternalName behavior

Create a LoadBalancer Service:

```powershell
@'
apiVersion: v1
kind: Service
metadata:
  name: echo-lb
  namespace: ch027
spec:
  type: LoadBalancer
  selector:
    app: echo
  ports:
    - name: http
      port: 80
      targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: external-docs
  namespace: ch027
spec:
  type: ExternalName
  externalName: docs.example.org
'@ | Set-Content -Encoding ascii .\external-services.yaml
kubectl --context kind-k8s-admin-ch027 apply -f .\external-services.yaml
kubectl --context kind-k8s-admin-ch027 -n ch027 get services echo-lb external-docs -o wide
kubectl --context kind-k8s-admin-ch027 -n ch027 describe service echo-lb
kubectl --context kind-k8s-admin-ch027 -n ch027 exec client -- nslookup external-docs.ch027.svc.cluster.local
```

**Expected:** `echo-lb` may show `EXTERNAL-IP: <pending>` in unmodified kind; `external-docs` has an external DNS target. DNS resolution to the external domain depends on network access and DNS; an ExternalName Service does not create Kubernetes backends.

**Do not install a load-balancer controller solely to turn Pending into success.** This lab tests your understanding of provider dependencies, not cloud provisioning.

## 17. Optional observation — kube-proxy or replacement datapath

```powershell
kubectl --context kind-k8s-admin-ch027 -n kube-system get daemonsets
kubectl --context kind-k8s-admin-ch027 -n kube-system get pods -o wide
kubectl --context kind-k8s-admin-ch027 get configmap -n kube-system kube-proxy -o yaml
```

The ConfigMap may be absent if the cluster uses a replacement datapath. Do not treat absence alone as a defect. In kind, kube-proxy is commonly present. Inspect the configured mode; do not infer the mode solely from the presence of a DaemonSet.

For managed EKS, AKS and GKE clusters, use the platform-specific documentation and approved observability tools. Avoid direct modifications to kube-proxy or eBPF maps during an incident without a validated recovery plan.

## 18. Failure diagnosis: a structured decision tree

```text
Client cannot reach Service
 |
 +-- DNS resolution fails?
 |     -> CoreDNS, resolv.conf, NetworkPolicy, DNS name
 |
 +-- Service exists and ClusterIP allocated?
 |     -> service spec, namespace, admission
 |
 +-- EndpointSlices contain ready backends?
 |     No -> selector, labels, readiness, targetPort
 |
 +-- Direct Pod IP works?
 |     No -> Pod app, CNI, network policy, routing
 |
 +-- Direct Pod IP works, ClusterIP fails?
 |     -> kube-proxy/eBPF, conntrack, Service policy
 |
 +-- Only external LB fails?
       -> provider controller, firewall, health check,
          LB class, subnet, target registration, quotas
```

### Troubleshooting matrix

| Symptom | Likely cause | Verification | Remediation |
|---|---|---|---|
| Service DNS fails | CoreDNS, DNS policy, typo | nslookup, resolv.conf | Fix DNS path or name |
| ClusterIP works, application returns 500 | App error | Logs/traces, HTTP response | Investigate app |
| No EndpointSlices/backends | Selector mismatch | Service selector vs Pod labels | Correct selector |
| Endpoint exists but not ready | Readiness probe fails | Pod conditions, EndpointSlice | Fix readiness/app |
| Direct Pod IP works, ClusterIP fails | Service datapath | Node/Service implementation | Follow platform runbook |
| Only NodePort fails externally | Firewall or host exposure | Node IP, port, kind mapping | Fix approved edge path |
| LoadBalancer pending | Missing provider/controller | Service events, cloud controller | Provision supported integration |
| Uneven requests | Persistent connections, affinity | Flow/connection analysis | Tune client/L7 architecture |
| Client source IP unexpected | SNAT / traffic policy | Backend logs and policy | Review externalTrafficPolicy |
| Local traffic policy drops requests | No local endpoints | Pod/node placement | Restore local capacity or policy |
| Traffic fails during rollout | Readiness/termination timing | EndpointSlice conditions | Adjust probes/draining |
| ExternalName TLS errors | Host/SNI mismatch | TLS error and DNS target | Configure app/TLS correctly |

## 19. SRE production runbook

### A. Establish scope and impact

1. Record incident time, affected Service, namespace, cluster and change history.
2. Classify failures as DNS, Service IP, direct Pod IP, NodePort, external LB or application layer.
3. Compare behavior by node, availability zone, source client and protocol.
4. Capture latency, error rate, request volume, connection resets and rollout events.

### B. Capture read-only evidence

```powershell
kubectl --context kind-k8s-admin-ch027 -n ch027 get services -o wide
kubectl --context kind-k8s-admin-ch027 -n ch027 get pods -o wide
kubectl --context kind-k8s-admin-ch027 -n ch027 get endpointslices -o wide
kubectl --context kind-k8s-admin-ch027 -n ch027 get events --sort-by=.lastTimestamp
kubectl --context kind-k8s-admin-ch027 -n ch027 describe service echo
kubectl --context kind-k8s-admin-ch027 -n ch027 describe deployment echo
```

In real environments, replace the context and namespace only after approved access verification. Never dump Secrets or unrelated workloads.

### C. Narrow the fault

1. Check Service selector and Pod labels.
2. Check EndpointSlice `ready`, `serving`, `terminating` conditions.
3. Compare direct Pod IP, ClusterIP and DNS.
4. Inspect Service port-to-targetPort mapping.
5. Identify kube-proxy/eBPF datapath and traffic policies.
6. For external failures, inspect LB controller events, targets, health checks and network ACLs.
7. Verify client connection reuse, keep-alive, retries and timeouts.

### D. Recover and validate

1. Prefer the smallest source-of-truth correction; avoid broad Service deletion.
2. Preserve the previous Service manifest and controller settings for rollback.
3. Validate all Ready backends, Service HTTP and application-level SLOs.
4. Verify cross-node and cross-zone paths, external ingress and source-IP expectations.
5. Record root cause, contributing factors and preventive alert changes.

### Stateful workloads

PostgreSQL, Redis, MongoDB, Elasticsearch and Kafka require application-aware routing. A Service does **not** know which replica is primary or writable unless selectors, readiness and controllers encode that state. Do not place all database replicas behind one writable Service without validating leader routing and failover semantics.

## 20. Observability and alerting

Recommended signals:

- Ready endpoints versus desired replicas, by Service and namespace.
- DNS error rate and latency.
- Service connection failures and timeouts.
- Application HTTP/gRPC p95/p99, 5xx and retry rates.
- kube-proxy sync errors/latency **if kube-proxy exists**.
- eBPF datapath drops/forwarding metrics **if provided by your CNI**.
- Load-balancer target health and controller reconciliation errors.
- Conntrack utilization and drops when relevant.
- EndpointSlice churn during rollouts.

**Alert example:** Service has desired replicas > 0 but zero ready endpoints for a sustained window, with an application-impact condition. Avoid paging solely because an ExternalName Service has no Pod endpoints.

Metric names vary by Kubernetes version and monitoring stack; verify exported series before writing PromQL.

## 21. Acceptance matrix

| ID | Requirement | Evidence |
|---|---|---|
| A01 | Disposable cluster isolated | Correct context, Ready nodes |
| A02 | Backend 3/3 Ready | Deployment and Pod output |
| A03 | ClusterIP and EndpointSlices | Service and slice output |
| A04 | Service DNS/HTTP | nslookup and hostname response |
| A05 | Selector failure reproduced | Zero eligible endpoints, HTTP failure |
| A06 | Selector recovery | Ready endpoints, HTTP success |
| A07 | Readiness exclusion | Unready Pod not eligible |
| A08 | NodePort configured | NodePort and node-path test or documented limitation |
| A09 | Headless DNS | Multiple backend addresses |
| A10 | LoadBalancer dependency | Pending or provisioned status correctly interpreted |
| A11 | ExternalName behavior | DNS alias inspected |
| A12 | Service datapath identified | kube-proxy or replacement evidence |
| A13 | Recovery validation | Ready endpoints and successful HTTP |
| A14 | Cleanup and report | Sanitized evidence, cluster deleted |

A01–A07, A09–A11, A13–A14 are required. A08 may be marked **Blocked** if kind host/node network access prevents the NodePort test; A12 may be **Unknown** if inspection permissions or implementation obscure the datapath. Never mark a blocked or unknown test Passed.

### Incident report template

```markdown
# Chapter 027 — Service and Load Balancing Acceptance
Operator:
Reviewer:
UTC date:
Cluster context:
Kubernetes version:
Service datapath:
External LB controller:

| Test | Pass / Fail / Blocked / Not Run | Evidence |
|---|---|---|
| A01 | | |
| A02 | | |
| A03 | | |
| A04 | | |
| A05 | | |
| A06 | | |
| A07 | | |
| A08 | | |
| A09 | | |
| A10 | | |
| A11 | | |
| A12 | | |
| A13 | | |
| A14 | | |

Incident timeline:
Root cause:
Recovery and rollback:
Remaining risk:
Monitoring gaps:
Cleanup confirmation:
Reviewer decision:
```

## 22. Cleanup and rollback

**Only delete the disposable kind cluster and its dedicated namespace.**

```powershell
kubectl config current-context
kubectl --context kind-k8s-admin-ch027 get nodes
kubectl --context kind-k8s-admin-ch027 delete namespace ch027 --ignore-not-found
kind delete cluster --name k8s-admin-ch027
kind get clusters
Remove-Item .\kind-config.yaml, .\echo.yaml, .\client.yaml, .\unready.yaml, .\nodeport.yaml, .\headless.yaml, .\external-services.yaml -ErrorAction SilentlyContinue
```

Keep sanitized acceptance evidence before cleanup. Never delete production Services or modify cloud load-balancer annotations simply to reproduce a lab.

## 23. Knowledge check

1. Why is a ClusterIP not the same as a Pod IP?
2. How do port, targetPort, containerPort and nodePort differ?
3. What controls whether a Pod becomes a ready Service endpoint?
4. Why can Service DNS work when the Service has zero usable endpoints?
5. Why does ten HTTP requests not prove fair load balancing?
6. What changes when externalTrafficPolicy is Local?
7. How does a headless Service differ from a ClusterIP Service?
8. Why can LoadBalancer remain Pending on kind?
9. What does ExternalName do, and what does it not do?
10. Why do database writer Services need application-aware leader selection?

## 24. Status and next chapter

**Draft published.** Labs, expected outcomes and acceptance criteria are instructional; they have not been executed against a live cluster. Review and runtime validation are still required.

**Next:** Chapter 028 — CoreDNS and Service Discovery.
