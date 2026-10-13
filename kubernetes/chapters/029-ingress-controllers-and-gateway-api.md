# Chapter 029 — Ingress Controllers and Gateway API

**Track:** Kubernetes Administration · **Part 06 — Kubernetes Networking**  
**Status:** Draft — runtime validation and technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, platform engineers  
**Prerequisites:** Chapters 026–028; Windows PowerShell, kubectl, Docker Desktop/kind, Helm; a disposable cluster

## 1. Production scenario

A deployment is healthy and its ClusterIP Service works, but users receive HTTP 404, 502, or 503 through the public hostname. The failure could be at DNS, external load balancer, controller, route matching, Service port mapping, EndpointSlice readiness, or the application itself. The goal is to isolate each hop with evidence rather than restarting controllers blindly.

### Learning outcomes

1. Explain the L7 request path and how Ingress differs from Gateway API.
2. Install and inspect an Ingress controller safely in a disposable cluster.
3. Configure host and path routing, TLS termination, and backend Services.
4. Explain GatewayClass, Gateway, HTTPRoute, listeners, and reference permissions.
5. Diagnose routing, controller reconciliation, readiness, and certificate failures.
6. Complete seven reproducible hands-on labs with expected results and cleanup.
7. Build a production recovery and monitoring checklist.

## 2. Architecture

```text
Client -> DNS -> external LB / node port -> controller data plane
                                              |
                                              +-> Ingress or Gateway listener
                                                    |
                                                    +-> host/path/header match
                                                          |
                                                          +-> Service -> EndpointSlice -> Ready Pod
```

Ingress is a Kubernetes API resource for HTTP(S) routing; **an Ingress resource alone does nothing without a compatible controller**. A controller watches desired state and configures a proxy or cloud load balancer. Ingress remains supported, but the API is frozen; Gateway API offers a more expressive, role-oriented alternative.

Gateway API separates infrastructure and application responsibilities:

| Resource | Responsibility |
|---|---|
| GatewayClass | Names a controller and infrastructure implementation |
| Gateway | Declares listeners, addresses, and traffic entry points |
| HTTPRoute | Matches requests and forwards to backend Services |
| ReferenceGrant | Explicitly permits certain cross-namespace references |
| IngressClass | Associates an Ingress with its controller |

**Implementation caveat:** Gateway API CRDs and a conforming Gateway controller must both be installed. An Ingress controller does not automatically support Gateway API. Listener TLS, redirects, filters, and advanced policies depend on the chosen implementation and support level.

## 3. Preparation and safety

Use an isolated kind cluster. Do not run controller installation or cleanup commands against production.

```powershell
kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
helm version
kubectl api-resources | Select-String 'ingresses|gatewayclasses|httproutes'
```

Expected: a reachable cluster and Helm CLI. Gateway resources may not exist yet; this is normal until CRDs are installed. Set `$ns = "ch029"` and use this namespace for disposable resources.

## 4. Lab 1 — Backend and Service baseline

```powershell
$ns = "ch029"
kubectl create namespace $ns
kubectl -n $ns create deployment web --image=nginx:1.27
kubectl -n $ns expose deployment web --name=web --port=80 --target-port=80
kubectl -n $ns rollout status deployment/web --timeout=180s
kubectl -n $ns get pods,svc,endpointslices
kubectl -n $ns port-forward svc/web 8080:80
```

In a **second** PowerShell terminal:

```powershell
curl.exe -i http://127.0.0.1:8080/
```

Expected: HTTP 200 and the NGINX welcome page. Stop the port-forward with Ctrl+C. If the baseline fails, fix Pod readiness or Service selectors before investigating ingress.

## 5. Lab 2 — Install an Ingress controller

For this disposable lab use ingress-nginx from its official Helm chart. Verify current supported versions and project maintenance/security status before any production adoption; the chart and controller lifecycle may change.

```powershell
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm show chart ingress-nginx/ingress-nginx
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx `
  --namespace ingress-nginx --create-namespace `
  --set controller.service.type=ClusterIP
kubectl -n ingress-nginx rollout status deployment/ingress-nginx-controller --timeout=300s
kubectl get ingressclass
kubectl -n ingress-nginx get svc,pods
```

Expected: Ready controller and an IngressClass, commonly `nginx`. Inspect actual names; do not assume an external IP exists in kind. This is a **lab-only** ClusterIP controller, accessed by port-forward.

## 6. Lab 3 — Host and path routing

Create `ch029-ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web
  namespace: ch029
spec:
  ingressClassName: nginx
  rules:
    - host: web.ch029.test
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web
                port:
                  number: 80
```

```powershell
kubectl apply -f .\ch029-ingress.yaml
kubectl -n ch029 describe ingress web
kubectl -n ingress-nginx port-forward svc/ingress-nginx-controller 8081:80
```

In another terminal:

```powershell
curl.exe -i -H "Host: web.ch029.test" http://127.0.0.1:8081/
curl.exe -i -H "Host: unmatched.ch029.test" http://127.0.0.1:8081/
```

Expected: matching host routes to NGINX with HTTP 200; unmatched host normally returns a controller default response, often 404. Actual defaults vary. Stop port-forward after the test.

**Path precedence:** Kubernetes Ingress selects the longest matching path, with Exact preferred over Prefix for equal lengths. Rewrites and regex routing are controller-specific and should not be treated as portable Ingress behavior.

## 7. Lab 4 — TLS termination

Create a disposable self-signed certificate with OpenSSL installed locally (never reuse it in production):

```powershell
openssl req -x509 -nodes -days 2 -newkey rsa:2048 `
  -keyout ch029.key -out ch029.crt -subj "/CN=web.ch029.test" `
  -addext "subjectAltName=DNS:web.ch029.test"
kubectl -n ch029 create secret tls web-tls --cert=ch029.crt --key=ch029.key
```

Add this to the Ingress `spec`, alongside `rules`:

```yaml
  tls:
    - hosts:
        - web.ch029.test
      secretName: web-tls
```

Apply again, then:

```powershell
kubectl -n ingress-nginx port-forward svc/ingress-nginx-controller 8443:443
# Separate terminal; -k is acceptable ONLY for this self-signed lab
curl.exe -k -i --resolve web.ch029.test:8443:127.0.0.1 https://web.ch029.test:8443/
kubectl -n ch029 describe secret web-tls
```

Expected: TLS handshake succeeds and HTTP 200 is returned. In production, use trusted certificates, proper SANs, automated rotation, and expiry alerts; never disable certificate verification in real clients.

## 8. Lab 5 — Gateway API discovery and routing

Check CRDs and controllers before proceeding:

```powershell
kubectl get crd gatewayclasses.gateway.networking.k8s.io
kubectl get gatewayclass
kubectl get gateways -A
```

If absent, install a **version-pinned** Gateway API standard CRD bundle and a supported Gateway controller using its official documentation. Do not install an arbitrary unpinned URL into a production cluster. Confirm the controller's GatewayClass name before applying the following example; replace `REPLACE_WITH_GATEWAYCLASS`.

Create `ch029-gateway.yaml`:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: web-gateway
  namespace: ch029
spec:
  gatewayClassName: REPLACE_WITH_GATEWAYCLASS
  listeners:
    - name: http
      protocol: HTTP
      port: 80
      hostname: web.ch029.test
      allowedRoutes:
        namespaces:
          from: Same
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: web-route
  namespace: ch029
spec:
  parentRefs:
    - name: web-gateway
  hostnames:
    - web.ch029.test
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: web
          port: 80
```

```powershell
kubectl apply -f .\ch029-gateway.yaml
kubectl -n ch029 get gateway,httproute
kubectl -n ch029 describe gateway web-gateway
kubectl -n ch029 describe httproute web-route
```

Expected: Gateway `Accepted=True` and `Programmed=True`, HTTPRoute `Accepted=True` and `ResolvedRefs=True` **only if** a compatible controller is installed and configuration is valid. If these conditions are missing or False, inspect events and controller logs. To test HTTP traffic, use the controller-specific Gateway address or supported local port-forward procedure; no universal Service name exists.

## 9. Lab 6 — Reproduce and diagnose a routing failure

Temporarily break the Ingress backend Service name:

```powershell
kubectl -n ch029 patch ingress web --type=json `
  -p '[{"op":"replace","path":"/spec/rules/0/http/paths/0/backend/service/name","value":"missing-service"}]'
kubectl -n ch029 describe ingress web
kubectl -n ch029 get svc web
kubectl -n ch029 get endpointslices -l kubernetes.io/service-name=web
kubectl -n ingress-nginx logs deployment/ingress-nginx-controller --tail=100
```

Retest the matching host through the Lab 3 port-forward. Expected: upstream failure, often HTTP 503, though exact status depends on controller. Restore:

```powershell
kubectl apply -f .\ch029-ingress.yaml
kubectl -n ch029 describe ingress web
```

If TLS was added in Lab 4, preserve that configuration in the saved manifest before reapplying. Confirm HTTP 200 after restoration.

## 10. Lab 7 — Gateway API failure and recovery

If Lab 5 has a working controller, edit the HTTPRoute backend to a nonexistent Service and inspect:

```powershell
kubectl -n ch029 describe httproute web-route
kubectl -n ch029 get httproute web-route -o yaml
kubectl -n ch029 get svc,endpointslices
```

Expected: `ResolvedRefs=False` with a relevant reason such as `BackendNotFound`, depending on implementation and reconciliation timing. Restore `backendRefs.name: web` by reapplying `ch029-gateway.yaml`; wait for `ResolvedRefs=True`. An invalid backend may result in HTTP 500 for matching traffic under Gateway API rules; do not assume the Ingress controller's 503 behavior applies.

## 11. Production troubleshooting matrix

| Symptom | Likely investigation | Evidence / recovery |
|---|---|---|
| DNS name does not resolve | Public/private DNS record, LB address | `Resolve-DnsName`, verify DNS and advertised address |
| 404 | Wrong Host header, path, listener, route acceptance | `describe ingress/httproute`, controller logs, curl Host |
| 502 | Upstream connection/reset/protocol mismatch | Proxy logs, app logs, backend protocol and port |
| 503 | No healthy upstreams, empty endpoints, backend unavailable | `get endpointslices`, Pod readiness, Service selectors |
| TLS warning | Expired cert, SAN mismatch, wrong Secret or SNI | Inspect cert chain, hostname, listener/Ingress TLS |
| Timeout | LB health checks, firewall, NetworkPolicy, proxy or app latency | Trace hop by hop, metrics, packet capture if approved |
| Gateway not programmed | Missing/unsupported controller or invalid listener | GatewayClass controller, conditions, events, logs |
| Route not attached | ParentRefs, allowedRoutes, hostname/listener mismatch | HTTPRoute parents and conditions |

**Triage sequence:** client DNS → LB address/health → controller Pods and Service → Ingress/Gateway route conditions → backend Service port → EndpointSlice addresses and readiness → application logs. Correlate timestamps, request IDs, and recent changes.

### Safe production commands

```powershell
kubectl get ingress -A
kubectl get ingressclass
kubectl get gatewayclass,gateway,httproute -A
kubectl -n <namespace> describe ingress <name>
kubectl -n <namespace> get svc <service> -o yaml
kubectl -n <namespace> get endpointslices -l kubernetes.io/service-name=<service>
kubectl -n <namespace> get events --sort-by=.lastTimestamp
```

Replace placeholders before running. Avoid indiscriminate controller restarts, broad policy deletion, or changing DNS during an incident without confirming cause.

## 12. Monitoring and SLO guidance

Track controller availability, request volume, 4xx/5xx by host and route, P50/P95/P99 latency, upstream connect failures, active connections, configuration reload/reconciliation errors, Gateway/HTTPRoute conditions, LB health, certificate expiration, and backend EndpointSlice readiness. Instrument the application separately to distinguish proxy errors from app responses.

Example alert ideas (adapt to actual metric names and traffic baseline):
- Sustained 5xx error-budget burn for a critical route.
- No Ready controller replicas or Gateway `Programmed=False`.
- Unexpected zero ready backend endpoints.
- TLS certificate expiring within 14 days.
- Reconciliation errors after a configuration change.

Use short and long burn-rate windows to avoid alerting on low-traffic noise.

## 13. Security and operational practices

- Pin and regularly review controller images, charts, and Gateway API CRD versions.
- Use RBAC, namespace ownership, admission policies, and scoped controller permissions.
- Apply NetworkPolicy and cloud security groups at appropriate layers.
- Terminate TLS deliberately; decide whether backend TLS/mTLS is also required.
- Keep Secrets out of Git; automate certificate issuance and renewal.
- Review cross-namespace Gateway routes and `ReferenceGrant` permissions.
- Test controller upgrades, configuration rollback, and failure-zone resilience.
- Document cloud-specific annotations and load balancer behavior separately from portable Kubernetes APIs.
- Prefer gradual migration: inventory Ingress features, verify Gateway implementation support, canary, compare behavior, then switch traffic with rollback ready.

## 14. Cleanup

Only in the disposable lab cluster:

```powershell
kubectl delete namespace ch029
helm uninstall ingress-nginx -n ingress-nginx
kubectl delete namespace ingress-nginx
```

Do **not** delete cluster-wide Gateway API CRDs or shared Gateway controllers just to clean up this lab. Remove only resources you explicitly installed and own.

## 15. Acceptance checklist

- [ ] Baseline Service returns HTTP 200.
- [ ] Ingress controller is Ready and its IngressClass is identified.
- [ ] Matching host/path routes correctly; unmatched host is rejected/defaulted.
- [ ] Lab TLS succeeds with expected hostname; self-signed status understood.
- [ ] GatewayClass and Gateway API prerequisites are identified.
- [ ] HTTPRoute conditions are verified with a compatible controller.
- [ ] Broken backend is diagnosed from controller/route and EndpointSlice evidence.
- [ ] Configuration is restored and requests succeed.
- [ ] Monitoring, TLS rotation, access controls, and rollback are documented.
- [ ] Disposable resources are cleaned up without touching shared infrastructure.

**Validation status:** Authoring complete; command execution, version compatibility, Gateway-controller-specific testing, and independent technical review remain pending.

## 16. Further reading

- [Kubernetes Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [Kubernetes Ingress Controllers](https://kubernetes.io/docs/concepts/services-networking/ingress-controllers/)
- [Gateway API documentation](https://gateway-api.sigs.k8s.io/)
- [Gateway API HTTP routing](https://gateway-api.sigs.k8s.io/guides/http-routing/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)

**Next:** Chapter 030 — Kubernetes NetworkPolicies and Network Security (Part 06 capstone).
