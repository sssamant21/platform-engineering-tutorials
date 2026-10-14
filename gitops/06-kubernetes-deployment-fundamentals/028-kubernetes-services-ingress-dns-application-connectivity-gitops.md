# Chapter 028 — Kubernetes Services, Ingress, DNS and Application Connectivity for GitOps

**Part 06 — Kubernetes Deployment Fundamentals** | **Chapter 028 / 100**  
**Audience:** Kubernetes SRE, infrastructure and platform engineers  
**Platforms:** AWS EKS, Azure AKS, Google GKE  
**Reference environment:** A single Kubernetes cluster with separate \`demo-dev\`, \`demo-test\`, \`demo-staging\` and \`demo-prod\` namespaces, each managed through environment-specific GitOps desired state.

> **Lab safety:** Use a disposable namespace and generic sample applications only. Do not create public load balancers, change shared DNS zones, or modify production ingress controllers without authorization. Kubernetes Services, Ingress resources and NetworkPolicies are distinct layers; a resource existing does not prove that traffic is routed or secured.

## 1. Learning objectives

After this chapter, you can:

1. Explain Pod IPs, Services, EndpointSlices, kube-proxy/service dataplanes and cluster DNS.
2. Compare ClusterIP, NodePort, LoadBalancer and headless Services.
3. Configure an internal Service for a digest-pinned application.
4. Diagnose selectors, endpoints, target ports, readiness and DNS failures.
5. Explain Ingress controller responsibilities, host/path routing and TLS.
6. Understand Gateway API as an alternative for supported controllers.
7. Enforce ingress/egress connectivity with NetworkPolicy without breaking DNS.
8. Apply GitLab CI validation and Argo CD reconciliation boundaries.
9. Compare EKS, AKS and GKE connectivity integrations.
10. Perform an SRE incident investigation and rollback.

## 2. Networking reference architecture

\`\`\`text
GitLab CI
  -> image build / security validation / immutable OCI digest
  -> reviewed GitOps change
  -> Argo CD Application per namespace
  -> Kubernetes API
        |
        +--> Deployment -> ready Pods
        |                  ^
        +--> ClusterIP Service -> EndpointSlices
        |                  ^
        +--> Ingress / Gateway -> controller / data plane
        |                  ^
        +--> DNS name -> load balancer / ingress address
        |
        +--> NetworkPolicy ingress/egress constraints
\`\`\`

A Service selects endpoints, while an Ingress or Gateway routes inbound HTTP(S) traffic using a controller. DNS only resolves names; it does not establish application readiness.

## 3. Kubernetes network building blocks

| Component | Responsibility | SRE inspection |
| --- | --- | --- |
| Pod IP | Pod network identity | \`kubectl get pods -o wide\` |
| Service ClusterIP | Stable virtual service endpoint | Service IP, selector, ports |
| EndpointSlice | Backend endpoint inventory and readiness | EndpointSlice addresses/conditions |
| CoreDNS | Internal name resolution | DNS Pods, ConfigMap, queries |
| kube-proxy/eBPF dataplane | Service forwarding implementation | Platform/CNI diagnostics |
| Ingress | HTTP(S) routing rules | Controller, class, status, events |
| Gateway API | Role-oriented traffic routing APIs | Installed CRDs/controller, route conditions |
| NetworkPolicy | Pod traffic restrictions | CNI support, allow/deny tests |
| External load balancer | Entry point outside cluster | Cloud LB health, firewall, target groups |

A Service without matching ready Pods may exist but provide no useful backend. A NetworkPolicy requires a CNI implementation that enforces it.

## 4. Service types

| Type | Typical use | Operational note |
| --- | --- | --- |
| ClusterIP | Internal application traffic | Default Service type |
| NodePort | Expose a port on nodes | Avoid broad internet exposure |
| LoadBalancer | Cloud-managed LB | Cost, firewall and lifecycle implications |
| ExternalName | DNS alias to another name | Does not proxy or validate external service |
| Headless (\`clusterIP: None\`) | Direct endpoint discovery | Common for stateful systems |

Ingress is not itself a Service type. It requires a compatible controller. Gateway API similarly requires installed CRDs and an implementing controller.

## 5. Lab prerequisites

- An authorized disposable \`demo-dev\` namespace.
- A digest-pinned image of \`demo-app\` exposing \`GET /healthz\` on port 8080 (Chapter 026).
- \`kubectl\` and permissions for Deployment, Service and optional NetworkPolicy.
- For optional ingress tests, an installed controller and approved test hostname.
- For optional DNS tests, a debugging Pod image approved by your organization.

Verify context:

\`\`\`bash
kubectl config current-context
kubectl auth can-i create deployments -n demo-dev
kubectl auth can-i create services -n demo-dev
kubectl get ingressclass
kubectl get gatewayclass
\`\`\`

An empty IngressClass/GatewayClass list does not mean Kubernetes networking is broken; it may mean no compatible ingress/gateway implementation is installed.

## 6. Lab A — Deploy a Service-backed application

Create \`k8s/deployment.yaml\`:

\`\`\`yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-app
  namespace: demo-dev
  labels:
    app.kubernetes.io/name: demo-app
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app.kubernetes.io/name: demo-app
  template:
    metadata:
      labels:
        app.kubernetes.io/name: demo-app
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: demo-app
          image: registry.example.com/training/demo-app@sha256:REPLACE_WITH_ACTUAL_DIGEST
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8080
          startupProbe:
            httpGet:
              path: /healthz
              port: http
            failureThreshold: 12
            periodSeconds: 5
          readinessProbe:
            httpGet:
              path: /healthz
              port: http
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            periodSeconds: 10
          resources:
            requests:
              cpu: 100m
              memory: 64Mi
            limits:
              cpu: 500m
              memory: 256Mi
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
\`\`\`

Replace the image placeholder with a **real registry digest**. Confirm registry pull permissions and node architecture. Never deploy the placeholder as-is.

Create \`k8s/service.yaml\`:

\`\`\`yaml
apiVersion: v1
kind: Service
metadata:
  name: demo-app
  namespace: demo-dev
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: demo-app
  ports:
    - name: http
      protocol: TCP
      port: 80
      targetPort: http
\`\`\`

Server-side validation and deployment:

\`\`\`bash
kubectl apply --dry-run=server -f k8s/deployment.yaml
kubectl apply --dry-run=server -f k8s/service.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl rollout status deployment/demo-app -n demo-dev --timeout=180s
kubectl get deployment,pods,service -n demo-dev -o wide
\`\`\`

Expected: two ready Pods and one ClusterIP Service.

## 7. Lab B — Verify endpoints and service connectivity

\`\`\`bash
kubectl get endpointslices -n demo-dev \
  -l kubernetes.io/service-name=demo-app -o wide
kubectl describe service demo-app -n demo-dev
kubectl get pods -n demo-dev -l app.kubernetes.io/name=demo-app \
  -o custom-columns=NAME:.metadata.name,IP:.status.podIP,READY:.status.containerStatuses[0].ready
\`\`\`

Use local port forwarding:

\`\`\`bash
kubectl port-forward -n demo-dev service/demo-app 8080:80
\`\`\`

In a second terminal:

\`\`\`bash
curl --fail --silent http://127.0.0.1:8080/healthz
\`\`\`

Expected: \`{"status":"ok"}\`.

Stop port forwarding with Ctrl+C. On Windows PowerShell, use \`Invoke-RestMethod http://127.0.0.1:8080/healthz\`.

**Interpretation:** A successful port-forward validates a path to a selected backend, but does not by itself validate all cluster DNS, CNI or NetworkPolicy paths.

## 8. Lab C — DNS and service discovery

Typical same-namespace name:

\`\`\`text
demo-app
\`\`\`

Cross-namespace name:

\`\`\`text
demo-app.demo-dev.svc.cluster.local
\`\`\`

The DNS suffix is commonly \`cluster.local\` but may be customized. Inspect the cluster's configured search domains rather than assuming a fixed suffix.

From an approved disposable debug Pod:

\`\`\`bash
kubectl run dns-check -n demo-dev --restart=Never \
  --image=busybox:1.36 --command -- sleep 600
kubectl wait --for=condition=Ready pod/dns-check -n demo-dev --timeout=120s
kubectl exec -n demo-dev dns-check -- nslookup demo-app
kubectl exec -n demo-dev dns-check -- nslookup demo-app.demo-dev.svc.cluster.local
kubectl delete pod dns-check -n demo-dev --ignore-not-found
\`\`\`

This optional command uses a training image tag. For production-grade or restricted clusters, replace it with an approved digest-pinned debug image; if the image is not allowed, skip rather than bypassing policy.

Expected: the Service resolves to its ClusterIP. For headless Services, DNS behavior differs.

### CoreDNS troubleshooting

\`\`\`bash
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl get service -n kube-system kube-dns
kubectl get events -n kube-system --sort-by=.lastTimestamp
\`\`\`

Labeling and DNS deployment names vary across providers. Do not modify shared CoreDNS configuration during this lab.

## 9. Lab D — Ingress and TLS reference

An Ingress resource alone does not create a functioning route. It needs an installed compatible controller, an IngressClass, network reachability, and (for HTTPS) a valid certificate.

Create \`k8s/ingress.yaml\` only after confirming the approved ingress class and hostname:

\`\`\`yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: demo-app
  namespace: demo-dev
spec:
  ingressClassName: REPLACE_WITH_APPROVED_CLASS
  tls:
    - hosts:
        - demo-dev.example.com
      secretName: demo-dev-tls
  rules:
    - host: demo-dev.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: demo-app
                port:
                  name: http
\`\`\`

**Template only:** Replace the class and hostname with approved values; \`demo-dev-tls\` must exist and contain an authorized certificate/key, usually provisioned by a certificate controller or approved secret integration. Do not create public DNS or certificates as an unapproved lab step.

Validate:

\`\`\`bash
kubectl apply --dry-run=server -f k8s/ingress.yaml
kubectl describe ingress demo-app -n demo-dev
kubectl get ingress demo-app -n demo-dev
\`\`\`

After an authorized deployment, validate the hostname and TLS chain using \`curl -v https://<approved-hostname>/healthz\`. Avoid \`curl -k\` as a way to declare TLS success.

## 10. Gateway API overview

Gateway API separates infrastructure ownership and application routing:

- \`GatewayClass\`: controller implementation.
- \`Gateway\`: listener and traffic entry point.
- \`HTTPRoute\`: HTTP matching and backend routing.
- \`ReferenceGrant\`: controlled cross-namespace reference permissions.

A Gateway API deployment requires installed CRDs, a compatible controller, and approved listener/TLS configuration. Do not assume it replaces an existing Ingress controller automatically.

Example HTTPRoute **template**:

\`\`\`yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: demo-app
  namespace: demo-dev
spec:
  parentRefs:
    - name: approved-gateway
      namespace: gateway-system
  hostnames:
    - demo-dev.example.com
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: demo-app
          port: 80
\`\`\`

A cross-namespace route attachment requires the Gateway listener to allow that namespace and may be constrained by platform policy. Confirm \`Accepted\` and \`ResolvedRefs\` conditions, not just resource creation.

## 11. Lab E — NetworkPolicy and DNS allowances

A default-deny egress policy can block DNS resolution. Do not apply it to a shared namespace without a complete, tested allowlist.

Example **reference-only** default-deny:

\`\`\`yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: demo-dev
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
\`\`\`

Example ingress allow from **within the same namespace** to demo-app on port 8080:

\`\`\`yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-demo-app-internal
  namespace: demo-dev
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: demo-app
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector: {}
      ports:
        - protocol: TCP
          port: 8080
\`\`\`

This does **not** allow external ingress-controller Pods in other namespaces. Their access must be separately authorized. DNS egress allowances must match actual CoreDNS Pod labels/namespaces and DNS ports (UDP/TCP 53); cluster DNS architectures vary. Validate with real connectivity tests.

**Important:** NetworkPolicy is generally additive allow policy, and enforcement depends on the CNI. A network policy object present in the API is not proof of traffic isolation.

## 12. EKS, AKS and GKE considerations

| Concern | EKS | AKS | GKE |
| --- | --- | --- | --- |
| Service LoadBalancer | AWS cloud LB integration | Azure Load Balancer integration | Google Cloud Load Balancing |
| Ingress / Gateway | AWS Load Balancer Controller or other approved controller | Application Gateway for Containers / approved ingress controller | GKE Ingress / Gateway controllers |
| Pod networking | Amazon VPC CNI or configured alternative | Azure CNI variants | GKE dataplane modes |
| DNS | CoreDNS | CoreDNS | Cluster DNS implementation |
| NetworkPolicy | CNI/engine dependent | Network policy engine dependent | Dataplane / NetworkPolicy configuration |
| Identity | EKS Pod Identity or IRSA | Microsoft Entra Workload ID | Workload Identity Federation for GKE |

Provider controllers and available features vary by cluster version and installation. Verify installed components before using cloud-specific annotations. A \`LoadBalancer\` Service may incur charges and create externally reachable infrastructure; avoid it in this lab.

## 13. GitLab CI and GitOps operational separation

GitLab CI should:

1. Validate YAML and Helm rendering.
2. Run unit/integration and security checks.
3. Build and publish one immutable image digest.
4. Verify signature, SBOM and provenance.
5. Propose a reviewed GitOps digest or routing change.

Argo CD should:

1. Reconcile the approved Kubernetes desired state.
2. Report sync/health status and drift.
3. Apply changes according to approved sync policy.
4. Preserve a traceable deployment history.

Avoid giving untrusted merge-request jobs cluster-admin or DNS administration credentials.

### Validation pipeline template

\`\`\`yaml
kubernetes_network_manifest_validation:
  stage: validate
  image: registry.example.com/platform/kubectl@sha256:<APPROVED_TOOL_DIGEST>
  tags: [mr-validation]
  script:
    - kubectl apply --dry-run=client -f k8s/deployment.yaml
    - kubectl apply --dry-run=client -f k8s/service.yaml
\`\`\`

This is a **template** requiring an approved tool image and a resolved workload digest. Client-side dry run is not proof of successful cluster admission or network connectivity.

## 14. Failure injection and recovery

Run only in the disposable namespace.

| Test | Fault | Expected observation | Recovery |
| --- | --- | --- | --- |
| A | Service selector mismatch | No ready endpoints | Restore labels/selector |
| B | Wrong \`targetPort\` | DNS works; traffic fails | Restore named port |
| C | Readiness path \`/missing\` | Pods excluded from Service endpoints | Restore \`/healthz\` |
| D | Invalid image digest | ImagePullBackOff; rollout stalls | Restore verified digest |
| E | Invalid hostname/TLS | HTTPS validation fails | Restore authorized host/cert |
| F | Default-deny without DNS allowance | DNS queries fail | Apply approved allow policy / revert |
| G | Missing ingress controller | Ingress exists without functioning route | Install/configure controller through platform change |
| H | Cross-namespace route not permitted | HTTPRoute rejected/unaccepted | Correct listener policy and grants |

Do not apply Tests E–H to shared production ingress, DNS or gateway resources.

### Key diagnostic commands

\`\`\`bash
kubectl get pods,svc,ingress -n demo-dev -o wide
kubectl get endpointslices -n demo-dev -l kubernetes.io/service-name=demo-app
kubectl describe service demo-app -n demo-dev
kubectl describe ingress demo-app -n demo-dev
kubectl get events -n demo-dev --sort-by=.lastTimestamp
kubectl logs deployment/demo-app -n demo-dev --tail=100
kubectl rollout status deployment/demo-app -n demo-dev --timeout=120s
\`\`\`

## 15. SRE incident response runbook

**Scenario:** Users report intermittent HTTP 503 errors after a GitOps routing change.

1. Identify the affected namespace, hostname, application and change commit.
2. Confirm DNS resolves to the intended ingress/load balancer.
3. Inspect ingress/gateway controller health, configuration and route conditions.
4. Check Service selector, port and ready EndpointSlices.
5. Check Deployment rollout, Pod readiness, restarts and application logs.
6. Review NetworkPolicy and cloud firewall changes.
7. Compare Git desired state with Argo CD live state.
8. Revert the faulty GitOps change through an approved MR or break-glass procedure.
9. Verify recovery using health checks, HTTP error rates and latency SLIs.
10. Document root cause, blast radius, timeline and preventive actions.

**Avoid** making untracked \`kubectl\` fixes that Argo CD will immediately reverse.

## 16. Observability and alerting

Track:

- Service availability and ready endpoint count.
- HTTP 4xx/5xx, p95/p99 latency and request volume.
- Ingress/Gateway controller reconciliation errors.
- TLS certificate expiration and handshake errors.
- CoreDNS errors, latency and saturation.
- CNI/NetworkPolicy drops and connectivity failures.
- Load balancer target health and backend failures.
- Argo CD OutOfSync/Degraded conditions.
- Rollout failure rate and image pull errors.

Set alert thresholds using measured baselines and business SLOs, not arbitrary sample numbers.

## 17. Cleanup

Only remove resources created for this lab:

\`\`\`bash
kubectl delete -f k8s/service.yaml --ignore-not-found
kubectl delete -f k8s/deployment.yaml --ignore-not-found
\`\`\`

If you created an Ingress, HTTPRoute, NetworkPolicy or debug Pod in an isolated lab, remove it through the approved process. Do not delete shared gateway/controller resources or namespaces. For Argo CD-managed objects, clean up through GitOps.

## 18. Acceptance checklist

- [ ] Correct cluster context and namespace verified.
- [ ] Workload uses a real immutable image digest.
- [ ] Two ready Pods and a ClusterIP Service exist.
- [ ] EndpointSlices contain healthy backends.
- [ ] Port-forwarded health check succeeds.
- [ ] DNS service discovery validated or limitation documented.
- [ ] Ingress controller/class and TLS requirements understood.
- [ ] Gateway API ownership and route conditions understood.
- [ ] NetworkPolicy DNS and ingress dependencies documented.
- [ ] Service selector/port/readiness failure tests completed.
- [ ] GitLab CI and Argo CD responsibilities separated.
- [ ] GitOps rollback and SRE runbook reviewed.
- [ ] No unauthorized public networking changes made.

## 19. Evidence worksheet

\`\`\`text
CHAPTER 028 — SERVICES, INGRESS, DNS AND CONNECTIVITY
Date:
Cluster / cloud:
Namespace:
Approved image digest:
Deployment ready/desired:
Service ClusterIP / port / targetPort:
EndpointSlice ready endpoints:
Port-forward health response:
Internal DNS result:
IngressClass / GatewayClass:
Ingress or HTTPRoute conditions (if tested):
TLS verification (if tested):
NetworkPolicy enforcement / DNS allowances:
Cloud LB health (if applicable):
Selector failure and recovery:
TargetPort failure and recovery:
Readiness failure and recovery:
GitOps change and rollback plan:
Reviewer:
Open risks / owners:
\`\`\`

## 20. Knowledge checks

1. Why can a Service exist without reachable backends?
2. How do EndpointSlices relate to Pod readiness?
3. What does CoreDNS do, and what does it not do?
4. Why does an Ingress need a controller?
5. How does Gateway API separate infrastructure and application routing?
6. Why can default-deny egress break DNS?
7. Why is a successful port-forward not proof of external ingress health?
8. Which networking failure domains are shared by Dev/Test/Staging/Prod namespaces in one cluster?

## 21. Completion

**Pass:** The operator demonstrates a healthy digest-pinned Deployment behind a ClusterIP Service, validates EndpointSlices and DNS, diagnoses common routing failures, and documents safe ingress/gateway and NetworkPolicy practices.

**Next: Chapter 029 — Kubernetes Deployment Strategies, Health Checks, Autoscaling and Release Reliability.**
