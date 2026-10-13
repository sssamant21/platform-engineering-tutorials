# Chapter 028 — CoreDNS and Service Discovery

**Track:** Kubernetes Administration · **Part 06 — Kubernetes Networking**  
**Status:** Draft — runtime validation and technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, platform engineers  
**Prerequisites:** Chapters 026–027; Docker Desktop, kind, kubectl and Windows PowerShell

## 1. Production scenario

An application reports intermittent `UnknownHostException` and database connection timeouts following a Kubernetes rollout. Direct connections to the database Pod IP work, but resolving `db.production.svc.cluster.local` sometimes fails. Other Pods resolve the same name successfully.

A DNS incident can originate from the application resolver, Pod `/etc/resolv.conf`, CoreDNS, upstream DNS, a Service or EndpointSlice configuration, node-local DNS caching, or network policies. This chapter teaches a systematic, evidence-driven investigation rather than assuming CoreDNS is the cause.

### Learning outcomes

1. Explain the Kubernetes DNS architecture and CoreDNS request path.
2. Resolve Services, headless Services and StatefulSet Pod DNS names.
3. Distinguish DNS A/AAAA, SRV, CNAME and search-domain behavior.
4. Interpret `dnsPolicy`, `dnsConfig`, `ndots` and resolver caching.
5. Read CoreDNS Corefile plugins and identify upstream forwarding dependencies.
6. Diagnose NXDOMAIN, SERVFAIL, timeouts, stale answers and DNS latency.
7. Use seven disposable-cluster labs to reproduce and recover common failures.
8. Define monitoring, safe recovery and production acceptance checks.

## 2. DNS architecture

```text
Application resolver
       |
       v
Pod /etc/resolv.conf
  nameserver = cluster DNS IP
  search = namespace.svc.cluster.local, svc.cluster.local, cluster.local
  options = ndots:5 (common, not universal)
       |
       v
CoreDNS Service (kube-dns)
       |
       +--> kubernetes plugin --> Services / EndpointSlices / Pod DNS records
       |
       +--> cache / loop / health / ready / errors
       |
       +--> forward plugin --> upstream DNS resolvers
                                  |
                                  +--> external domains
```

The Service often named `kube-dns` is a stable ClusterIP fronting CoreDNS Pods. The Service name does not imply the old kube-dns implementation is running.

The **CoreDNS control plane** watches Kubernetes resources through the API. Its **DNS data plane** receives queries and responds using configured plugins. DNS itself does not forward HTTP or database packets.

## 3. Kubernetes DNS naming

For a typical cluster with DNS domain `cluster.local`:

| Resource | Example name | Typical answer |
|---|---|---|
| ClusterIP Service | `api.ch028.svc.cluster.local` | Service ClusterIP (A/AAAA) |
| Headless Service | `db.ch028.svc.cluster.local` | Ready endpoint IP addresses |
| Named Service port | `_http._tcp.api.ch028.svc.cluster.local` | SRV record |
| StatefulSet Pod with headless governing Service | `db-0.db.ch028.svc.cluster.local` | Pod endpoint IP when published |
| ExternalName Service | `docs.ch028.svc.cluster.local` | CNAME to configured external name |

The cluster DNS domain is configurable. Verify the actual value from Pod resolver settings and CoreDNS configuration; do not assume every cluster uses `cluster.local`.

### ClusterIP versus headless DNS

A normal ClusterIP Service typically resolves to the stable virtual IP. A headless Service with `clusterIP: None` resolves to endpoint addresses. DNS answers for headless Services are subject to endpoint readiness, publication settings, caching and timing.

### StatefulSet identities

A StatefulSet with `serviceName: db` and a matching headless Service can give Pods stable DNS identities such as `db-0.db.ch028.svc.cluster.local`. Stable identity does **not** guarantee that the Pod is Ready, the database is leader, or the storage is healthy.

If clients need to discover unready peers during bootstrap, `publishNotReadyAddresses: true` may be appropriate for carefully designed clustered applications; it also exposes unready endpoints and must not be used casually for client traffic.

## 4. Resolver search domains and ndots

A typical Pod resolver file looks like:

```text
nameserver 10.96.0.10
search ch028.svc.cluster.local svc.cluster.local cluster.local
options ndots:5
```

These values are examples only. With `ndots:5`, a name with fewer than five dots may be attempted against search domains before an absolute lookup. This can increase DNS queries for external names and affect latency.

Use a trailing dot for an absolute fully qualified DNS name where supported, for example `api.ch028.svc.cluster.local.`. Applications and language runtimes may have their own resolver behavior and caches; `nslookup` results are not necessarily identical to Java, Go, glibc or musl resolution behavior.

## 5. Pod DNS policies

| dnsPolicy | Behavior | Common use |
|---|---|---|
| `ClusterFirst` | Cluster DNS for Kubernetes names, upstream forwarding for other names | Default normal Pods |
| `Default` | Inherits node resolver configuration | Special workloads |
| `ClusterFirstWithHostNet` | Cluster DNS for hostNetwork Pods | Host-network agents |
| `None` | Uses explicit `dnsConfig` | Specialized resolver configurations |

A `hostNetwork: true` Pod should normally specify `ClusterFirstWithHostNet` if it needs cluster DNS. The behavior of node resolver inheritance can vary by runtime and node OS.

### Explicit DNS configuration

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: dns-custom
spec:
  dnsPolicy: None
  dnsConfig:
    nameservers:
      - 1.1.1.1
    searches:
      - example.org
    options:
      - name: ndots
        value: "2"
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
```

**Production warning:** This example uses a public resolver only to illustrate configuration. It would usually **not** resolve private Kubernetes Service names and may violate corporate DNS policy. Do not deploy it in a real workload without an approved resolver design.

## 6. CoreDNS Corefile and plugins

A representative Corefile (not necessarily identical to your cluster):

```text
.:53 {
    errors
    health {
        lameduck 5s
    }
    ready
    kubernetes cluster.local in-addr.arpa ip6.arpa {
        pods insecure
        fallthrough in-addr.arpa ip6.arpa
        ttl 30
    }
    prometheus :9153
    forward . /etc/resolv.conf {
        max_concurrent 1000
    }
    cache 30
    loop
    reload
    loadbalance
}
```

### Plugin responsibilities

- `kubernetes`: serves Kubernetes resource records based on API watches.
- `forward`: forwards queries to upstream resolvers.
- `cache`: caches positive and negative answers subject to configuration.
- `errors`: logs DNS processing errors.
- `health` and `ready`: expose health and readiness endpoints.
- `prometheus`: exposes CoreDNS metrics when enabled.
- `loop`: detects certain forwarding loops at startup.
- `reload`: reloads Corefile changes when supported.
- `loadbalance`: can randomize ordering of multi-address answers; it does not replace a Service datapath.

**Caution:** Plugin behavior, syntax and metrics depend on the CoreDNS version and packaged configuration. Changing the Corefile can break DNS cluster-wide. Use version-controlled configuration and a staged rollout.

## 7. DNS failure taxonomy

| Symptom | Meaning / common cause | First checks |
|---|---|---|
| NXDOMAIN | Name does not exist in DNS view | Spelling, namespace, Service existence |
| SERVFAIL | Resolver failed to answer | CoreDNS errors, upstream, plugin failures |
| Timeout | No response within client deadline | Network path, DNS Service, policy, overload |
| NOERROR with no answer | Name exists but requested record unavailable | Record type, endpoints, IPv4/IPv6 |
| Stale IP | Client or CoreDNS cache retains old data | TTL, app cache, rollout timing |
| Slow resolution | Search expansion, upstream latency, retries | ndots, resolver metrics, upstream |
| Intermittent failures | Load, endpoint churn, packet loss, node-local issues | Node/Pod distribution, DNS logs |
| Works by IP, fails by name | DNS path issue | Resolver config, CoreDNS, network |
| Name resolves, TCP fails | Not necessarily DNS | Service, EndpointSlice, CNI, policy, app |

A DNS answer alone does not guarantee the target Service has ready endpoints or that the application is accepting connections.

## 8. Production architecture patterns

### NodeLocal DNSCache

NodeLocal DNSCache, where installed, places a DNS caching agent on nodes to reduce query latency and pressure on cluster DNS. Its deployment, listening addresses and routing depend on the distribution and networking mode. Do not assume it is present or that every Pod uses it.

### Upstream split-horizon DNS

Organizations often need internal zones, private endpoints and on-premises DNS forwarding. A forwarding misconfiguration can break only corporate domains while Kubernetes Service names continue working.

### Managed Kubernetes

- **EKS:** CoreDNS add-on versions, VPC DNS settings, upstream connectivity and optional node-local caching affect behavior.
- **AKS:** CoreDNS configuration and Azure DNS/private DNS integration vary by cluster networking and private endpoint setup.
- **GKE:** Managed DNS features and datapath options can change observability and configuration access.

Never edit provider-managed CoreDNS components without reviewing supported customization paths.

## 9. Lab environment — isolated kind cluster

Use Windows PowerShell. All kubectl mutations explicitly target the disposable context.

```powershell
docker version
kind version
kubectl version --client
New-Item -ItemType Directory -Force .\k8s-ch028 | Out-Null
Set-Location .\k8s-ch028
@'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
'@ | Set-Content -Encoding ascii .\kind-config.yaml
kind create cluster --name k8s-admin-ch028 --config .\kind-config.yaml --wait 180s
kubectl config current-context
kubectl --context kind-k8s-admin-ch028 get nodes -o wide
kubectl --context kind-k8s-admin-ch028 create namespace ch028
```

**Expected:** context `kind-k8s-admin-ch028`, three Ready nodes and namespace `ch028`. Stop if the cluster is not isolated, Docker is unhealthy or nodes are not Ready.

## 10. Lab A — Inspect cluster DNS architecture

```powershell
kubectl --context kind-k8s-admin-ch028 -n kube-system get deployment coredns
kubectl --context kind-k8s-admin-ch028 -n kube-system get pods -l k8s-app=kube-dns -o wide
kubectl --context kind-k8s-admin-ch028 -n kube-system get service kube-dns -o wide
kubectl --context kind-k8s-admin-ch028 -n kube-system get endpointslices -l kubernetes.io/service-name=kube-dns
kubectl --context kind-k8s-admin-ch028 -n kube-system get configmap coredns -o yaml
```

**Expected:** CoreDNS Deployment, ready Pods, kube-dns Service and a Corefile in the ConfigMap. Actual labels, replica counts and plugins may vary with kind/Kubernetes versions.

Record: DNS Service IP, CoreDNS replica count, Corefile Kubernetes zone, upstream forwarding and cache settings. **Read-only inspection only.**

## 11. Lab B — Service DNS and search domains

Create a web backend and ClusterIP Service:

```powershell
@'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch028
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: nginx
          image: nginx:stable
          ports:
            - name: http
              containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: http
            periodSeconds: 3
          resources:
            requests:
              cpu: 20m
              memory: 32Mi
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: ch028
spec:
  selector:
    app: web
  ports:
    - name: http
      port: 80
      targetPort: http
---
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: ch028
spec:
  containers:
    - name: tools
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\baseline.yaml

kubectl --context kind-k8s-admin-ch028 apply --dry-run=server -f .\baseline.yaml
kubectl --context kind-k8s-admin-ch028 apply -f .\baseline.yaml
kubectl --context kind-k8s-admin-ch028 -n ch028 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch028 -n ch028 wait --for=condition=Ready pod/client --timeout=180s
kubectl --context kind-k8s-admin-ch028 -n ch028 exec client -- cat /etc/resolv.conf
kubectl --context kind-k8s-admin-ch028 -n ch028 exec client -- nslookup web
kubectl --context kind-k8s-admin-ch028 -n ch028 exec client -- nslookup web.ch028.svc.cluster.local
kubectl --context kind-k8s-admin-ch028 -n ch028 exec client -- wget -qO- http://web.ch028.svc.cluster.local/
```

**Expected:** `web` resolves within the namespace, FQDN resolves to ClusterIP, and HTTP succeeds. Compare the DNS answer with `kubectl get service web -o wide`.

## 12. Lab C — Headless Service and endpoint DNS

Create a headless Service selecting the web Pods:

```powershell
@'
apiVersion: v1
kind: Service
metadata:
  name: web-headless
  namespace: ch028
spec:
  clusterIP: None
  selector:
    app: web
  ports:
    - name: http
      port: 80
      targetPort: http
'@ | Set-Content -Encoding ascii .\headless.yaml

kubectl --context kind-k8s-admin-ch028 apply -f .\headless.yaml
kubectl --context kind-k8s-admin-ch028 -n ch028 get service web-headless
kubectl --context kind-k8s-admin-ch028 -n ch028 get endpointslices -l kubernetes.io/service-name=web-headless -o wide
kubectl --context kind-k8s-admin-ch028 -n ch028 exec client -- nslookup web-headless.ch028.svc.cluster.local
```

**Expected:** `CLUSTER-IP: None`, two ready backend IPs in EndpointSlices, and DNS answers containing endpoint IP addresses. Ordering and response count can vary with timing and caching.

## 13. Lab D — Reproduce NXDOMAIN and distinguish missing names

```powershell
kubectl --context kind-k8s-admin-ch028 -n ch028 exec client -- nslookup does-not-exist.ch028.svc.cluster.local
kubectl --context kind-k8s-admin-ch028 -n ch028 get service does-not-exist
kubectl --context kind-k8s-admin-ch028 -n ch028 get service web
```

**Expected:** missing name returns a negative DNS response, and Kubernetes confirms the Service does not exist. The working `web` Service remains available.

**Recovery:** correct the application's Service name/namespace or create the intended Service through approved deployment configuration. Do not restart CoreDNS to fix a nonexistent record.

For a real incident, also inspect namespace typos, stale app configuration, and the effective cluster DNS suffix.

## 14. Lab E — DNS policy contrast

Create a Pod using `dnsPolicy: Default`, which inherits the kind node's resolver configuration:

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: node-dns
  namespace: ch028
spec:
  dnsPolicy: Default
  containers:
    - name: tools
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\node-dns.yaml

kubectl --context kind-k8s-admin-ch028 apply -f .\node-dns.yaml
kubectl --context kind-k8s-admin-ch028 -n ch028 wait --for=condition=Ready pod/node-dns --timeout=180s
kubectl --context kind-k8s-admin-ch028 -n ch028 exec node-dns -- cat /etc/resolv.conf
kubectl --context kind-k8s-admin-ch028 -n ch028 exec node-dns -- nslookup web.ch028.svc.cluster.local
```

**Expected:** `node-dns` resolver settings may differ from `client`. The lookup may fail or succeed depending on kind's node resolver/upstream configuration. **Do not assume failure is deterministic.** Record actual resolver and result.

**Lesson:** DNS policy can change the resolution path without any CoreDNS outage.

## 15. Lab F — CoreDNS readiness and safe observability

```powershell
kubectl --context kind-k8s-admin-ch028 -n kube-system get deployment coredns
kubectl --context kind-k8s-admin-ch028 -n kube-system describe deployment coredns
kubectl --context kind-k8s-admin-ch028 -n kube-system logs deployment/coredns --tail=100 --prefix=true
kubectl --context kind-k8s-admin-ch028 -n kube-system get configmap coredns -o yaml
kubectl --context kind-k8s-admin-ch028 -n kube-system get events --sort-by=.lastTimestamp
```

**Expected:** CoreDNS health and logs can be inspected. Not every DNS query appears in logs; the `log` plugin may not be enabled. Avoid enabling verbose query logging across a production cluster without evaluating volume and data exposure.

**Do not scale CoreDNS to zero, delete the kube-dns Service or intentionally break the Corefile.** Such actions are unnecessarily disruptive for this chapter.

### Optional metrics

If CoreDNS exposes a Prometheus endpoint and the environment permits port-forwarding, inspect `/metrics` with approved tools. Metric names differ across CoreDNS versions. Typical families include request counts, response codes, request durations, cache hits and forwarder failures. Verify series existence before writing alerts.

## 16. Lab G — Service name correction and recovery

Create a disposable Service alias that initially has the wrong selector:

```powershell
@'
apiVersion: v1
kind: Service
metadata:
  name: web-alias
  namespace: ch028
spec:
  selector:
    app: nonexistent
  ports:
    - port: 80
      targetPort: 80
'@ | Set-Content -Encoding ascii .\alias.yaml

kubectl --context kind-k8s-admin-ch028 apply -f .\alias.yaml
kubectl --context kind-k8s-admin-ch028 -n ch028 exec client -- nslookup web-alias.ch028.svc.cluster.local
kubectl --context kind-k8s-admin-ch028 -n ch028 get endpointslices -l kubernetes.io/service-name=web-alias
kubectl --context kind-k8s-admin-ch028 -n ch028 exec client -- wget -T 3 -qO- http://web-alias.ch028.svc.cluster.local/
```

**Expected:** the ClusterIP name resolves, but the Service has no ready endpoints and HTTP fails. This is **not a DNS failure**.

Correct the selector:

```powershell
kubectl --context kind-k8s-admin-ch028 -n ch028 patch service web-alias --type=merge -p '{"spec":{"selector":{"app":"web"}}}'
kubectl --context kind-k8s-admin-ch028 -n ch028 get endpointslices -l kubernetes.io/service-name=web-alias -o wide
kubectl --context kind-k8s-admin-ch028 -n ch028 exec client -- wget -qO- http://web-alias.ch028.svc.cluster.local/
```

**Expected:** ready endpoints appear after reconciliation and HTTP succeeds. This proves why the DNS layer must be checked separately from Service routing.

## 17. Optional StatefulSet DNS design example

For production stateful systems, use a governing headless Service and a StatefulSet with matching `serviceName`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: db-peers
spec:
  clusterIP: None
  selector:
    app: db
  ports:
    - name: postgres
      port: 5432
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: db
spec:
  serviceName: db-peers
  replicas: 3
  selector:
    matchLabels:
      app: db
  template:
    metadata:
      labels:
        app: db
    spec:
      containers:
        - name: postgres
          image: postgres:16
          env:
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: password
          ports:
            - name: postgres
              containerPort: 5432
```

**Illustration only — do not deploy as a production database.** This lacks persistent storage, replication, backups, security hardening and a provisioned Secret. A three-replica PostgreSQL StatefulSet does not automatically form a replicated PostgreSQL cluster.

Typical peer DNS names: `db-0.db-peers.namespace.svc.cluster.local`, `db-1...`, `db-2...`. Application failover and writer routing remain separate concerns.

## 18. Production DNS troubleshooting decision tree

```text
Application cannot resolve/connect
 |
 +-- DNS query returns NXDOMAIN?
 |     -> verify exact name, namespace, Service, cluster domain
 |
 +-- DNS query times out?
 |     -> Pod resolver, DNS Service IP, NetworkPolicy, CNI, CoreDNS health
 |
 +-- SERVFAIL?
 |     -> CoreDNS plugin/upstream failures, forwarding loops, DNSSEC/path
 |
 +-- DNS resolves but IP is unexpected?
 |     -> ClusterIP vs headless, stale cache, split-horizon
 |
 +-- DNS resolves correctly but TCP/HTTP fails?
 |     -> Service selector, EndpointSlices, targetPort, CNI, app
 |
 +-- Only external domains fail?
 |     -> forward plugin, upstream DNS, NAT/egress, private zones
 |
 +-- Only some nodes or Pods fail?
       -> node-local cache, per-node network, DNS policy, app resolver
```

## 19. Incident response and SRE runbook

### A. Scope and impact

- Identify affected applications, namespaces, nodes, DNS names and time window.
- Determine whether the failure affects Kubernetes Service names, external domains, or both.
- Compare the same query from affected and healthy Pods.
- Record request failure rate, DNS latency, connection errors and recent changes.

### B. Read-only triage

```powershell
kubectl --context kind-k8s-admin-ch028 -n ch028 get pods -o wide
kubectl --context kind-k8s-admin-ch028 -n ch028 get services,endpointslices
kubectl --context kind-k8s-admin-ch028 -n kube-system get deployment coredns
kubectl --context kind-k8s-admin-ch028 -n kube-system get service kube-dns
kubectl --context kind-k8s-admin-ch028 -n kube-system get pods -l k8s-app=kube-dns -o wide
kubectl --context kind-k8s-admin-ch028 -n kube-system logs deployment/coredns --tail=100 --prefix=true
kubectl --context kind-k8s-admin-ch028 -n ch028 get events --sort-by=.lastTimestamp
```

In production, replace the context and namespace only after explicit authorization. Avoid collecting sensitive DNS query logs without an approved data-handling process.

### C. Isolation

1. Read `/etc/resolv.conf` from the affected Pod.
2. Query the exact FQDN, then a short name.
3. Compare ClusterIP Service versus headless behavior.
4. Check CoreDNS Service endpoints and Pod readiness.
5. Check Corefile `kubernetes`, `forward`, `cache` and `loop` settings.
6. Check NetworkPolicy, node-local caching and upstream connectivity.
7. If DNS works, inspect Service EndpointSlices and the application datapath.

### D. Recovery

- Fix wrong names/selectors at the source of truth.
- Restore failed CoreDNS replicas only after confirming the root cause.
- Correct upstream forwarding through a controlled change.
- Avoid mass CoreDNS restarts as a default action; they may amplify load and cache misses.
- Validate affected applications, not just `nslookup`.

### E. Validation

- DNS success rate and latency recovered.
- Application connection success and error rate recovered.
- Service endpoints and backend readiness healthy.
- No node/zone-specific failures remain.
- Monitoring, incident timeline, rollback and preventive controls documented.

## 20. Observability and alert design

Track the following, subject to metric availability:

- CoreDNS DNS request volume by response code.
- DNS request duration percentiles.
- SERVFAIL/NXDOMAIN rates segmented by zone and application impact.
- CoreDNS Pod availability, restarts and CPU/memory usage.
- Upstream forwarding failures and latency.
- Cache hit/miss rates.
- DNS Service EndpointSlice ready endpoint count.
- NodeLocal DNSCache health where installed.
- Application DNS lookup errors and connection timeouts.

**Alerting guidance:** A high NXDOMAIN count can be normal for search-domain expansion or discovery; correlate with application failures. Prefer sustained SERVFAIL/timeouts and impact-based alerts over isolated DNS response codes.

### Suggested operational SLOs (illustrative)

| SLI | Example objective | Caveat |
|---|---|---|
| Internal Service DNS success | 99.9% over 30 days | Exclude legitimately nonexistent names |
| Internal DNS p99 latency | Under 100 ms | Set from observed baseline |
| CoreDNS ready replicas | At least 2 where designed | Small lab clusters may differ |
| Upstream failure rate | Near zero sustained | Segment internal/external zones |

These are examples, **not measured or guaranteed cluster values**.

## 21. Evidence and acceptance

```powershell
New-Item -ItemType Directory -Force .\evidence | Out-Null
(Get-Date).ToUniversalTime().ToString("o") | Set-Content .\evidence\capture-time-utc.txt
kubectl --context kind-k8s-admin-ch028 get nodes -o wide > .\evidence\nodes.txt
kubectl --context kind-k8s-admin-ch028 -n ch028 get pods -o wide > .\evidence\pods.txt
kubectl --context kind-k8s-admin-ch028 -n ch028 get services,endpointslices > .\evidence\services-endpoints.txt
kubectl --context kind-k8s-admin-ch028 -n ch028 get events --sort-by=.lastTimestamp > .\evidence\events.txt
kubectl --context kind-k8s-admin-ch028 -n kube-system get deployment coredns > .\evidence\coredns-deployment.txt
```

Sanitize evidence before sharing. Do not export Secrets or customer DNS query payloads.

| ID | Acceptance check | Expected evidence |
|---|---|---|
| A01 | Isolated kind cluster | Correct context and Ready nodes |
| A02 | CoreDNS architecture inspected | Deployment, Service, Corefile |
| A03 | Service FQDN resolves | ClusterIP matches DNS |
| A04 | Short name resolves | Search-domain behavior observed |
| A05 | Service HTTP works | NGINX response |
| A06 | Headless DNS works | Endpoint IP answers |
| A07 | Missing name diagnosed | NXDOMAIN/negative answer |
| A08 | dnsPolicy contrast observed | Resolver settings compared |
| A09 | CoreDNS logs/health inspected | Read-only evidence |
| A10 | Selector failure isolated from DNS | DNS succeeds, HTTP fails |
| A11 | Selector corrected | Ready endpoints and HTTP |
| A12 | Evidence and cleanup | Sanitized report, cluster removed |

A01–A07 and A09–A12 are mandatory. A08 is observational; record the actual result rather than assuming `Default` DNS will fail.

### Incident report template

```markdown
# Chapter 028 — DNS and Service Discovery Acceptance
Operator:
Reviewer:
UTC date:
Cluster context:
Kubernetes version:
CoreDNS version:
Cluster DNS domain:
CoreDNS Service IP:
NodeLocal DNSCache installed? Yes / No / Unknown

| ID | Pass / Fail / Blocked / Not Run | Evidence |
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

Timeline:
Root cause:
Recovery validation:
Rollback:
Remaining risk:
Preventive alerts:
Cleanup confirmation:
Reviewer decision:
```

## 22. Cleanup

**Only delete the dedicated disposable kind cluster.**

```powershell
kubectl config current-context
kubectl --context kind-k8s-admin-ch028 get nodes
kubectl --context kind-k8s-admin-ch028 delete namespace ch028 --ignore-not-found
kind delete cluster --name k8s-admin-ch028
kind get clusters
Remove-Item .\kind-config.yaml, .\baseline.yaml, .\headless.yaml, .\node-dns.yaml, .\alias.yaml -ErrorAction SilentlyContinue
```

Retain sanitized evidence. Never delete or scale down CoreDNS in a shared environment to reproduce an outage.

## 23. Knowledge check

1. Why is the Service named `kube-dns` even when CoreDNS runs?
2. What is the difference between ClusterIP and headless Service DNS?
3. Why can `nslookup` succeed while an application cannot connect?
4. How does `ndots` affect search-domain expansion and latency?
5. When is `ClusterFirstWithHostNet` appropriate?
6. What does the CoreDNS `kubernetes` plugin do?
7. How does the `forward` plugin relate to external domains?
8. Why might `Default` DNS policy fail to resolve cluster Service names?
9. Why is a missing Service not fixed by restarting CoreDNS?
10. What additional safeguards are needed for StatefulSet database discovery?

## 24. Status and next chapter

**Draft published.** The commands and expected results have not been executed in this session. Runtime validation and technical review are required before marking this chapter complete.

**Next:** Chapter 029 — Ingress Controllers and Gateway API.
