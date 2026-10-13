# Chapter 030 — Kubernetes NetworkPolicies and Network Security

**Track:** Kubernetes Administration · **Part 06 — Kubernetes Networking (final capstone)**  
**Status:** Draft — runtime validation and technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, platform engineers  
**Prerequisites:** Chapters 026–029; kubectl, Windows PowerShell, a disposable cluster with NetworkPolicy-capable CNI

## 1. Production scenario

An internal API must accept connections from an approved frontend but reject other workloads. The API also requires DNS and access to a database. A default-deny policy is deployed; suddenly DNS resolution fails and the application cannot connect to its database. Operators need to distinguish policy denial from DNS, Service, EndpointSlice, CNI, or application failure, and recover without broadly reopening traffic.

### Learning objectives

1. Explain NetworkPolicy's L3/L4 semantics and the difference between ingress and egress isolation.
2. Verify that the installed CNI actually enforces NetworkPolicy.
3. Implement namespace-wide default deny, allowlisted ingress, egress, and DNS exceptions.
4. Understand Pod and namespace selectors, additive policies, ports, and IPBlock caveats.
5. Reproduce and diagnose cross-namespace and DNS failures.
6. Validate enforcement using allowed and denied probes, not just API acceptance.
7. Produce a rollback plan, security acceptance report, and monitoring checklist.

## 2. Security architecture and limits

```text
client Pod (namespace: frontend)
       |
       | source Pod labels + source namespace labels
       v
CNI enforcement at Pod networking layer
       |
       +-- NetworkPolicy ingress allow? --+
       |                                   |
       +-- NetworkPolicy egress allow? ----+--> Service VIP / endpoint Pod --> app
                                               |
                                               +--> DNS resolution (separate egress)
```

NetworkPolicy is a **namespaced, declarative** API. Policies select Pods in their own namespace. If any ingress policy selects a Pod, ingress becomes isolated and only explicitly allowed ingress traffic is permitted. Egress isolation works independently. Multiple policies are **additive**: they allow a union of traffic and do not create ordered deny rules. For Pod-to-Pod traffic, both source egress and destination ingress must allow the connection when each side is isolated.

NetworkPolicy does **not** itself provide application-layer HTTP authorization, TLS, identity-based service authorization, or a general-purpose firewall for all host/node traffic. Standard NetworkPolicy supports TCP, UDP, and SCTP where supported; it cannot reliably express FQDN allowlists or HTTP paths. Some CNIs offer additional proprietary policy APIs.

**Important:** NetworkPolicy enforcement depends on the CNI. The Kubernetes API may accept resources even when no implementation enforces them. NetworkPolicy behavior around NAT, external load balancers, hostNetwork Pods, and node-originated traffic can vary. Validate actual packet paths in the target platform.

## 3. Lab prerequisites and safeguards

All labs are intended for a disposable cluster. **Do not run default-deny policies in production without an inventory, tested allow rules, and a rollback window.**

```powershell
kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
kubectl get pods -n kube-system -o wide
kubectl api-resources | Select-String networkpolicies
kubectl get networkpolicies -A
```

Use kind only with a NetworkPolicy-enforcing CNI such as a correctly configured Calico or Cilium installation. The default kind networking setup should **not** be assumed to enforce policies. Follow the selected CNI's documented kind installation procedure and verify compatibility with the Kubernetes version. Record the CNI name, version, and enforcement test result before continuing.

Lab design uses two namespaces and three client Pods:

- `ch030-app`: `api` and `client-internal`.
- `ch030-client`: `client-allowed` and `client-blocked`.
- The API is an NGINX deployment and ClusterIP Service on TCP 80.
- Client Pods use `busybox:1.36` and run `sleep 36000`.

## 4. Lab 1 — Deploy and verify the baseline

Save as `ch030-baseline.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch030-app
---
apiVersion: v1
kind: Namespace
metadata:
  name: ch030-client
  labels:
    access-group: approved
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: ch030-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
        - name: nginx
          image: nginx:1.27
          ports:
            - containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 2
            periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: ch030-app
spec:
  selector:
    app: api
  ports:
    - name: http
      port: 80
      targetPort: 80
---
apiVersion: v1
kind: Pod
metadata:
  name: client-internal
  namespace: ch030-app
  labels:
    role: internal
spec:
  containers:
    - name: busybox
      image: busybox:1.36
      command: ["sh", "-c", "sleep 36000"]
---
apiVersion: v1
kind: Pod
metadata:
  name: client-allowed
  namespace: ch030-client
  labels:
    role: allowed
spec:
  containers:
    - name: busybox
      image: busybox:1.36
      command: ["sh", "-c", "sleep 36000"]
---
apiVersion: v1
kind: Pod
metadata:
  name: client-blocked
  namespace: ch030-client
  labels:
    role: blocked
spec:
  containers:
    - name: busybox
      image: busybox:1.36
      command: ["sh", "-c", "sleep 36000"]
```

```powershell
kubectl apply -f .\ch030-baseline.yaml
kubectl -n ch030-app rollout status deployment/api --timeout=180s
kubectl -n ch030-app wait --for=condition=Ready pod/client-internal --timeout=120s
kubectl -n ch030-client wait --for=condition=Ready pod/client-allowed --timeout=120s
kubectl -n ch030-client wait --for=condition=Ready pod/client-blocked --timeout=120s
kubectl -n ch030-app get svc,endpointslices,pods
kubectl -n ch030-client exec client-allowed -- wget -q -T 3 -O - http://api.ch030-app.svc.cluster.local/
kubectl -n ch030-client exec client-blocked -- wget -q -T 3 -O - http://api.ch030-app.svc.cluster.local/
```

**Expected:** both clients retrieve the NGINX welcome page. Baseline success proves DNS, Service and backend are functional *before* applying policies.

## 5. Lab 2 — Namespace default-deny ingress and egress

Create `ch030-default-deny.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: ch030-app
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: ch030-client
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
```

```powershell
kubectl apply -f .\ch030-default-deny.yaml
kubectl get networkpolicy -A
kubectl -n ch030-client exec client-allowed -- wget -q -T 3 -O - http://api.ch030-app.svc.cluster.local/
```

**Expected with an enforcing CNI:** the request fails or times out. DNS may also fail because egress to CoreDNS is blocked. A successful request after propagation suggests either an existing additive allow policy, a non-enforcing CNI, or a testing-path issue. Inspect all policies and retest; never declare success based on policy objects alone.

## 6. Lab 3 — Restore DNS egress safely

Discover the actual DNS Service, endpoints and labels:

```powershell
kubectl -n kube-system get svc kube-dns -o wide
kubectl -n kube-system get pods --show-labels
kubectl -n kube-system get endpointslices -l kubernetes.io/service-name=kube-dns
```

The example below assumes CoreDNS Pods have label `k8s-app: kube-dns` and reside in namespace `kube-system`. **Verify and adjust labels first.** Namespace label `kubernetes.io/metadata.name` is normally set by Kubernetes, but verify it too.

Create `ch030-dns-egress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns-egress
  namespace: ch030-client
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns-egress
  namespace: ch030-app
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
```

```powershell
kubectl apply -f .\ch030-dns-egress.yaml
kubectl -n ch030-client exec client-allowed -- nslookup api.ch030-app.svc.cluster.local
```

**Expected:** DNS lookup succeeds, but HTTP still fails because API ingress and client egress are denied. If DNS does not recover, inspect CNI service NAT behavior, actual DNS endpoint labels, node-local DNS configuration, and whether the DNS Pods themselves have restrictive ingress policies. A NodeLocal DNSCache setup may need a different exception.

## 7. Lab 4 — Allow approved client traffic

Create `ch030-allow-api.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-approved-api-ingress
  namespace: ch030-app
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes: [Ingress]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              access-group: approved
          podSelector:
            matchLabels:
              role: allowed
      ports:
        - protocol: TCP
          port: 80
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-approved-api-egress
  namespace: ch030-client
spec:
  podSelector:
    matchLabels:
      role: allowed
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ch030-app
          podSelector:
            matchLabels:
              app: api
      ports:
        - protocol: TCP
          port: 80
```

The namespaceSelector and podSelector under **one** `from` item are ANDed. Separate list items would be ORed and could accidentally broaden access.

```powershell
kubectl apply -f .\ch030-allow-api.yaml
kubectl -n ch030-client exec client-allowed -- wget -q -T 3 -O - http://api.ch030-app.svc.cluster.local/
kubectl -n ch030-client exec client-blocked -- wget -q -T 3 -O - http://api.ch030-app.svc.cluster.local/
```

**Expected:** allowed client succeeds; blocked client fails. Retest several times after CNI reconciliation. If both succeed, check policy selectors, namespace labels, and actual enforcement.

## 8. Lab 5 — Same-namespace access and selector semantics

The `client-internal` Pod in `ch030-app` is blocked by default-deny egress, and the API has no matching ingress allow. Add both sides.

Create `ch030-internal.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-internal-api-ingress
  namespace: ch030-app
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              role: internal
      ports:
        - protocol: TCP
          port: 80
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-internal-api-egress
  namespace: ch030-app
spec:
  podSelector:
    matchLabels:
      role: internal
  policyTypes: [Egress]
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: api
      ports:
        - protocol: TCP
          port: 80
```

```powershell
kubectl apply -f .\ch030-internal.yaml
kubectl -n ch030-app exec client-internal -- wget -q -T 3 -O - http://api.ch030-app.svc.cluster.local/
```

**Expected:** internal client succeeds. A bare podSelector in a policy peer selects Pods in the policy's own namespace. Use namespaceSelector for cross-namespace access.

## 9. Lab 6 — Failure injection, diagnosis and rollback

Temporarily remove the approved ingress policy:

```powershell
kubectl -n ch030-app delete networkpolicy allow-approved-api-ingress
kubectl -n ch030-client exec client-allowed -- wget -q -T 3 -O - http://api.ch030-app.svc.cluster.local/
kubectl -n ch030-app get networkpolicy -o yaml
kubectl -n ch030-app get pods -o wide --show-labels
kubectl -n ch030-app get svc api -o yaml
kubectl -n ch030-app get endpointslices -l kubernetes.io/service-name=api
```

**Expected:** previously allowed client now fails; DNS should still work. Reapply `ch030-allow-api.yaml` and verify HTTP 200. Note that Kubernetes NetworkPolicy has no standard per-denied-packet event. Use CNI-specific policy verdict logs/flow visibility if available (for example, supported Cilium Hubble or Calico telemetry), with care for performance and sensitive metadata.

### Triage decision tree

```text
DNS lookup fails?
  -> DNS Service / CoreDNS health / DNS egress / node-local DNS
DNS works, Service has no ready endpoints?
  -> selector / Pod readiness / EndpointSlice
Endpoints healthy, Pod-IP and Service traffic fail?
  -> CNI routes / ingress+egress policies / app listener
Pod-IP works but Service fails?
  -> Service port / kube-proxy or eBPF Service datapath
Allowed and blocked clients both succeed?
  -> CNI enforcement / unintended additive allow / selectors / policy propagation
```

Never remove all policies cluster-wide to test a single route.

## 10. Lab 7 — Part 06 networking acceptance project

Collect evidence:

```powershell
kubectl get nodes -o wide
kubectl -n kube-system get pods -o wide
kubectl -n ch030-app get pods,svc,endpointslices,networkpolicies -o wide
kubectl -n ch030-client get pods,networkpolicies -o wide
kubectl -n ch030-client exec client-allowed -- nslookup api.ch030-app.svc.cluster.local
kubectl -n ch030-client exec client-allowed -- wget -q -T 3 -O - http://api.ch030-app.svc.cluster.local/
kubectl -n ch030-client exec client-blocked -- wget -q -T 3 -O - http://api.ch030-app.svc.cluster.local/
kubectl -n ch030-app exec client-internal -- wget -q -T 3 -O - http://api.ch030-app.svc.cluster.local/
```

Record an evidence table:

| Check | Required result |
|---|---|
| CNI enforcement | Verified by positive and negative tests |
| CoreDNS resolution | Success |
| API Service/EndpointSlice | Ready backend endpoint |
| Approved cross-namespace client | HTTP 200 |
| Unapproved cross-namespace client | Denied or timeout |
| Approved same-namespace client | HTTP 200 |
| Broken ingress policy injection | Failure reproduced |
| Policy restoration | Service recovered |
| Unexpected broad allow policies | None identified |

**Acceptance requires actual execution and evidence.** Do not mark Part 06 lab validated merely because manifests were published.

## 11. Production hardening

### Policy design

- Start with application traffic inventory: clients, backends, ports, DNS, observability, identity and external dependencies.
- Introduce default deny incrementally per namespace with prevalidated allow policies.
- Use stable, governance-controlled namespace and Pod labels; protect labels from unauthorized changes through RBAC and admission policies.
- Specify ingress and egress separately and validate both.
- Prefer scoped namespace+Pod selectors to broad namespace-wide access.
- Review `ipBlock` CIDRs carefully; their interaction with Service NAT and Pod IP ranges is implementation-dependent.
- Keep external egress controls at the appropriate cloud firewall, NAT, proxy, or CNI layer; standard NetworkPolicy cannot match domain names.
- Test probes, webhooks, metrics scraping, service mesh sidecars, and infrastructure agents before enforcing isolation.

### Operational controls

- Version-control policies with peer review and rollback commits.
- Use staging canaries and record allowed/denied traffic before rollout.
- Audit namespace labels, policy additions, and controller/CNI upgrades.
- Alert on sustained CNI health degradation, policy programming failures, DNS failure rates, and sudden service connection errors.
- Track security exceptions with owner, expiry, and justification.
- Revalidate policies after CNI upgrades, Service datapath changes, or network architecture changes.

## 12. Incident response runbook

1. **Scope:** identify source Pod, destination, namespace, protocol, port, time window and affected tenants.
2. **Baseline:** confirm Pods, readiness, Service, EndpointSlice and DNS before changing policies.
3. **Inspect:** list all selecting policies in both namespaces; remember allow rules are additive.
4. **Verify enforcement:** inspect CNI status and flow telemetry, and compare a known-good with a denied test Pod.
5. **Recover narrowly:** restore a specific previously approved rule or revert the exact change; avoid global allow-all.
6. **Validate:** rerun both positive and negative connectivity tests to ensure security remains effective.
7. **Document:** capture timeline, policy diff, CNI evidence, root cause, remediation and preventive action.

## 13. Cleanup

Only on the disposable cluster:

```powershell
kubectl delete namespace ch030-app ch030-client
```

Do not uninstall a shared CNI or delete cluster-wide resources as part of this chapter's cleanup.

## 14. Acceptance checklist

- [ ] NetworkPolicy-capable CNI verified by live enforcement test.
- [ ] Baseline connectivity established before applying restrictions.
- [ ] Default-deny ingress and egress demonstrated.
- [ ] DNS exception restored name resolution without reopening HTTP access.
- [ ] Approved client allowed and blocked client denied.
- [ ] Same-namespace client allowed with both ingress and egress rules.
- [ ] Failure injection and targeted rollback executed.
- [ ] EndpointSlice, DNS, CNI and policy failure domains distinguished.
- [ ] Production monitoring, access controls, exception process and rollback documented.
- [ ] Lab resources removed safely.

**Status:** Draft published; runtime validation, CNI-specific verification, and independent technical review pending.

## 15. Further reading

- [Kubernetes Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Kubernetes DNS for Services and Pods](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Cilium documentation](https://docs.cilium.io/)
- [Calico documentation](https://docs.tigera.io/calico/latest/)

**Part 06 writing milestone:** Chapters 026–030 drafted. Runtime validation remains pending.  
**Next:** Chapter 031 — Kubernetes Volumes, PVs and PVCs (Part 07 — Kubernetes Storage).
