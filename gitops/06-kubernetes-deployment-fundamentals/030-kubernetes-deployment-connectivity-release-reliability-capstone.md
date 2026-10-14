# Chapter 030 — Kubernetes Deployment, Connectivity and Release Reliability Capstone

**Part 06 — Final Capstone** | **Chapter 030 / 100**  
**Audience:** Kubernetes administrators, SREs, platform and DevOps engineers  
**Clouds:** Amazon EKS, Azure AKS and Google GKE  
**Reference architecture:** One Kubernetes cluster with separate namespaces \`demo-dev\`, \`demo-test\`, \`demo-staging\`, \`demo-prod\`.  
**Prior chapters:** 026 Deployments; 027 Configuration, Secrets and Isolation; 028 Services, Ingress and DNS; 029 Deployment Strategies, Autoscaling and Reliability.

> **Safety:** Run hands-on changes only in an approved disposable namespace. Use a real, previously verified immutable OCI image digest; never deploy placeholders. This capstone does not require public ingress, cloud load balancers, production credentials or production cluster access. Namespace separation is not complete security isolation.

## 1. Capstone mission

Deliver an operationally sound Kubernetes application platform and prove that the team can deploy, validate, troubleshoot and recover a release without bypassing GitOps governance.

The exercise covers:

1. A secure digest-pinned Deployment with probes and resource budgets.
2. Nonsecret ConfigMap-based configuration and controlled rollout.
3. ClusterIP Service, ready EndpointSlices and DNS discovery.
4. Optional authorized ingress/TLS and NetworkPolicy verification.
5. Rolling updates, HPA, PDB and availability constraints.
6. Negative tests and recovery for common application incidents.
7. GitLab CI validation, reviewed GitOps promotion and Argo CD reconciliation design.
8. SRE readiness scoring and operational evidence.

## 2. Reference architecture

\`\`\`text
GitLab source project
    |
    +--> MR: tests, manifest validation, security policies
    +--> protected pipeline: build/scan/sign image ONCE
    |
    v
OCI registry: demo-app@sha256:<VERIFIED_DIGEST>
    |
    v
Reviewed GitOps repository
    |
    +--> environments/dev/values.yaml
    +--> environments/test/values.yaml
    +--> environments/staging/values.yaml
    +--> environments/prod/values.yaml
    |
    v
Argo CD Applications (same Kubernetes cluster)
    |
    +--> demo-dev       +--> demo-test
    +--> demo-staging   +--> demo-prod
             |
      ConfigMap / Secret references
             |
      Deployment / ReplicaSets / Pods
             |
      ClusterIP Service / EndpointSlices
             |
      Optional Ingress / Gateway / DNS / TLS
             |
      SLOs, HPA, PDB and incident response
\`\`\`

GitLab CI produces and verifies the artifact; Argo CD reconciles reviewed GitOps desired state. Promotion reuses the **same image digest**. Application configuration varies per namespace. Production-critical workloads may need stronger isolation than a shared cluster.

## 3. Deliverables and acceptance evidence

| Deliverable | Evidence |
| --- | --- |
| Verified OCI artifact | Registry digest and approved source commit |
| Secure Deployment | Non-root, probes, resources, immutable digest |
| Configuration | ConfigMap, environment readback and update procedure |
| Service discovery | Ready EndpointSlices and HTTP health response |
| DNS | Approved in-cluster lookup |
| Rollout | Deployment history, availability and duration |
| Autoscaling | HPA status and metrics prerequisites |
| Disruption control | PDB status and allowed disruptions |
| Isolation | RBAC, Pod Security Admission, quota, NetworkPolicy review |
| GitOps workflow | Environment-specific values and approval plan |
| Failure recovery | Negative-test results and restored health |
| SRE assessment | Scoring, risk register and reviewer decision |

## 4. Capstone repository structure

\`\`\`text
demo-k8s-capstone/
├── README.md
├── src/
│   ├── __init__.py
│   └── server.py
├── tests/
│   └── test_server.py
├── Dockerfile
├── .dockerignore
├── k8s/
│   ├── configmap.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── hpa.yaml
│   ├── pdb.yaml
│   └── networkpolicy-review.yaml
├── gitops/
│   └── environments/
│       ├── dev/values.yaml
│       ├── test/values.yaml
│       ├── staging/values.yaml
│       └── prod/values.yaml
└── docs/
    ├── OPERATIONS-RUNBOOK.md
    └── ACCEPTANCE.md
\`\`\`

Create an empty \`src/__init__.py\`.

## 5. Build the sample application

\`src/server.py\`:

\`\`\`python
import json
import os
import signal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            code, body = 200, {"status": "ok"}
        elif self.path == "/config":
            code, body = 200, {
                "environment": os.getenv("APP_ENV", "unknown"),
                "feature_enabled": os.getenv("FEATURE_ENABLED", "false").lower() == "true",
            }
        else:
            code, body = 404, {"error": "not found"}
        payload = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main():
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    signal.signal(signal.SIGTERM, lambda *_: server.shutdown())
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
\`\`\`

**Note:** This training HTTP server illustrates endpoints and termination intent; Python's \`shutdown()\` must be called from a different thread than \`serve_forever()\` to avoid deadlock. Before production use, replace the SIGTERM handler with a proper threaded shutdown or an application server with tested graceful termination. For this lab, use the corrected implementation below instead of the handler above:

\`\`\`python
# Replace the signal.signal line in main() with:
import threading
signal.signal(
    signal.SIGTERM,
    lambda *_: threading.Thread(target=server.shutdown, daemon=True).start()
)
\`\`\`

\`tests/test_server.py\`:

\`\`\`python
import unittest
from unittest.mock import patch
from src.server import Handler


class ApplicationTests(unittest.TestCase):
    def test_handler_exists(self):
        self.assertTrue(callable(Handler))

    def test_environment_parsing(self):
        with patch.dict("os.environ", {"APP_ENV": "dev", "FEATURE_ENABLED": "true"}):
            import os
            self.assertEqual(os.getenv("APP_ENV"), "dev")
            self.assertEqual(os.getenv("FEATURE_ENABLED"), "true")


if __name__ == "__main__":
    unittest.main()
\`\`\`

These are smoke tests; an HTTP integration test is required before treating the service as production-ready.

\`Dockerfile\`:

\`\`\`dockerfile
# syntax=docker/dockerfile:1
# Training base tag; pin reviewed base digest for production.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY src/ /app/src/
USER 65532:65532
EXPOSE 8080
CMD ["python", "-m", "src.server"]
\`\`\`

\`.dockerignore\`:

\`\`\`dockerignore
.git/
.env
*.key
*.pem
tests/
k8s/
gitops/
docs/
__pycache__/
\`\`\`

Run:

\`\`\`bash
python -m unittest discover -s tests -v
docker build --pull -t demo-app:ch030 .
docker run --rm -d --name demo-app-ch030 \
  --read-only --cap-drop ALL --security-opt no-new-privileges \
  -p 127.0.0.1:8080:8080 demo-app:ch030
curl --fail --silent http://127.0.0.1:8080/healthz
docker stop demo-app-ch030
\`\`\`

**Important:** Publishing, scanning, signing and obtaining a real digest follow Chapters 021–025. Local image IDs are not registry manifest digests. Use an approved disposable registry for integration.

## 6. ConfigMap and Deployment

\`k8s/configmap.yaml\`:

\`\`\`yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: demo-app-config
  namespace: demo-dev
data:
  APP_ENV: dev
  FEATURE_ENABLED: "false"
\`\`\`

\`k8s/deployment.yaml\`:

\`\`\`yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-app
  namespace: demo-dev
  labels:
    app: demo-app
spec:
  replicas: 3
  revisionHistoryLimit: 5
  minReadySeconds: 5
  progressDeadlineSeconds: 180
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: demo-app
  template:
    metadata:
      labels:
        app: demo-app
    spec:
      automountServiceAccountToken: false
      terminationGracePeriodSeconds: 30
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: demo-app
          image: registry.example.com/training/demo-app@sha256:REPLACE_WITH_REAL_DIGEST
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8080
          envFrom:
            - configMapRef:
                name: demo-app-config
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
            timeoutSeconds: 2
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            periodSeconds: 10
            timeoutSeconds: 2
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

**Prerequisite:** Replace the placeholder with a real signed/verified image digest. The deployment will not work with the placeholder. Ensure namespace quota accommodates 3 replicas plus one surge Pod.

## 7. ClusterIP Service

\`k8s/service.yaml\`:

\`\`\`yaml
apiVersion: v1
kind: Service
metadata:
  name: demo-app
  namespace: demo-dev
spec:
  type: ClusterIP
  selector:
    app: demo-app
  ports:
    - name: http
      port: 80
      targetPort: http
\`\`\`

No external LoadBalancer or public ingress is required for the core lab.

## 8. Autoscaling and disruption control

\`k8s/hpa.yaml\`:

\`\`\`yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: demo-app
  namespace: demo-dev
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: demo-app
  minReplicas: 3
  maxReplicas: 6
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
\`\`\`

\`k8s/pdb.yaml\`:

\`\`\`yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: demo-app
  namespace: demo-dev
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: demo-app
\`\`\`

HPA requires metrics; PDB protects only certain voluntary evictions, not node failure. If the metrics API is absent, document the blocker and omit HPA from the live lab rather than bypassing admission policy.

## 9. NetworkPolicy review artifact

\`k8s/networkpolicy-review.yaml\`:

\`\`\`yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: demo-app-ingress-review
  namespace: demo-dev
spec:
  podSelector:
    matchLabels:
      app: demo-app
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector: {}
      ports:
        - protocol: TCP
          port: 8080
\`\`\`

**Review-only by default:** This allows same-namespace Pod ingress but may block ingress-controller traffic originating from other namespaces. Test your actual traffic topology and CNI enforcement before applying. Do not assume it permits DNS egress or external ingress.

## 10. Deployment and validation sequence

First verify context and permissions:

\`\`\`bash
kubectl config current-context
kubectl auth can-i create deployments -n demo-dev
kubectl auth can-i create services -n demo-dev
\`\`\`

Apply in this order:

\`\`\`bash
kubectl apply --dry-run=server -f k8s/configmap.yaml
kubectl apply --dry-run=server -f k8s/deployment.yaml
kubectl apply --dry-run=server -f k8s/service.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl rollout status deployment/demo-app -n demo-dev --timeout=240s
kubectl get deployments,replicasets,pods,services -n demo-dev -o wide
kubectl get endpointslices -n demo-dev \
  -l kubernetes.io/service-name=demo-app
\`\`\`

Then, if authorized and supported:

\`\`\`bash
kubectl apply -f k8s/pdb.yaml
kubectl get pdb demo-app -n demo-dev
kubectl top pods -n demo-dev
kubectl apply -f k8s/hpa.yaml
kubectl describe hpa demo-app -n demo-dev
\`\`\`

Expected: 3 ready replicas, ready Service endpoints, successful HTTP health and configuration checks. HPA may not scale without sustained load.

## 11. HTTP and configuration verification

\`\`\`bash
kubectl port-forward -n demo-dev service/demo-app 8080:80
\`\`\`

From a second terminal:

\`\`\`bash
curl --fail --silent http://127.0.0.1:8080/healthz
curl --fail --silent http://127.0.0.1:8080/config
\`\`\`

Expected:

\`\`\`json
{"status":"ok"}
\`\`\`

\`\`\`json
{"environment":"dev","feature_enabled":false}
\`\`\`

PowerShell alternative:

\`\`\`powershell
Invoke-RestMethod http://127.0.0.1:8080/healthz
Invoke-RestMethod http://127.0.0.1:8080/config
\`\`\`

Stop port-forward with Ctrl+C.

## 12. ConfigMap change acceptance

Edit \`FEATURE_ENABLED\` to \`"true"\` in \`k8s/configmap.yaml\`, then:

\`\`\`bash
kubectl apply -f k8s/configmap.yaml
kubectl rollout restart deployment/demo-app -n demo-dev
kubectl rollout status deployment/demo-app -n demo-dev --timeout=240s
\`\`\`

Expected: the \`/config\` endpoint returns \`feature_enabled: true\` after the new Pods become ready.

**GitOps caveat:** Updating ConfigMap data does not refresh environment variables in existing Pods. In managed environments, use a versioned ConfigMap or a checksum annotation in the Pod template so a reviewed Git change triggers a Deployment revision. Manual restart is only for the disposable lab.

## 13. GitOps environment promotion design

Suggested values layout:

\`\`\`text
gitops/environments/
  dev/values.yaml
  test/values.yaml
  staging/values.yaml
  prod/values.yaml
\`\`\`

Each file should contain nonsecret settings and a real immutable image digest:

\`\`\`yaml
image:
  repository: registry.example.com/training/demo-app
  digest: sha256:REPLACE_WITH_REAL_DIGEST
config:
  featureEnabled: false
\`\`\`

Promote the **same verified digest** through Dev → Test → Staging → Production using reviewed GitOps MRs and explicit production approval. Each environment is a namespace in the same cluster, managed by a distinct Argo CD Application.

These are reference values, not a complete Helm chart. Part 07 builds the chart; Parts 08–10 configure Argo CD.

## 14. GitLab CI validation design

GitLab CI should validate:

- YAML/Helm syntax and schema.
- Digest pinning and trusted supply-chain evidence.
- Resource requests, limits, probes and security context.
- ConfigMap and Secret references.
- Service selectors and ports.
- HPA/PDB compatibility.
- Environment-specific policy.
- Reviewed GitOps promotion.

Do not put broad production Kubernetes credentials in untrusted MR pipelines.

Illustrative GitLab job:

\`\`\`yaml
kubernetes_manifest_validation:
  stage: validate
  image: registry.example.com/platform/kubectl@sha256:<APPROVED_TOOL_DIGEST>
  tags: [mr-validation]
  script:
    - kubectl apply --dry-run=client -f k8s/configmap.yaml
    - kubectl apply --dry-run=client -f k8s/deployment.yaml
    - kubectl apply --dry-run=client -f k8s/service.yaml
\`\`\`

This is a template requiring an approved tool image and resolved workload digest. Client dry run is not equivalent to server admission or runtime testing.

## 15. Failure-injection matrix

Perform only in \`demo-dev\`, with a recorded rollback digest and resource baseline.

| Test | Fault | Expected result | Recovery |
| --- | --- | --- | --- |
| A | Invalid image digest | ImagePullBackOff, stalled rollout | Restore approved digest |
| B | Wrong readiness path | New Pods unready, endpoints reduced | Restore \`/healthz\` |
| C | Wrong liveness path | Container restarts | Restore \`/healthz\` |
| D | Wrong Service selector | No matching endpoints | Restore selector |
| E | Wrong Service targetPort | HTTP requests fail | Restore port |
| F | Missing ConfigMap | Pod config error | Restore ConfigMap |
| G | ConfigMap updated without restart | Old env var remains | Reviewed rollout |
| H | Insufficient CPU request headroom | Pending Pods / quota errors | Restore requests/capacity |
| I | HPA metrics unavailable | Unknown CPU metrics / no reliable scaling | Restore metrics |
| J | PDB too strict for maintenance | Voluntary eviction blocked | Review availability requirements |

For each test, capture: injected change, observed symptom, diagnostic command, root cause, recovery action and restored health. Do not drain shared nodes or disable shared metrics services.

## 16. Troubleshooting commands

\`\`\`bash
kubectl get deployment,replicaset,pods,svc,hpa,pdb -n demo-dev
kubectl describe deployment demo-app -n demo-dev
kubectl describe service demo-app -n demo-dev
kubectl get endpointslices -n demo-dev -l kubernetes.io/service-name=demo-app
kubectl get events -n demo-dev --sort-by=.lastTimestamp
kubectl logs -n demo-dev deployment/demo-app --tail=100
kubectl rollout history deployment/demo-app -n demo-dev
kubectl rollout status deployment/demo-app -n demo-dev --timeout=120s
kubectl describe hpa demo-app -n demo-dev
kubectl describe pdb demo-app -n demo-dev
kubectl top pods -n demo-dev
\`\`\`

Not all commands succeed in clusters without metrics or optional HPA/PDB resources. Record prerequisites rather than misclassifying these as application failures.

## 17. Incident response exercise

**Scenario:** After a reviewed digest promotion, users see elevated HTTP 503 and p99 latency while Kubernetes reports a partially healthy rollout.

### Investigation

1. Identify the source commit, GitOps MR, digest and namespace.
2. Compare error/latency SLIs before and after the release.
3. Inspect Deployment conditions, ReplicaSets and Pod readiness.
4. Check Service EndpointSlices and ingress/gateway health if applicable.
5. Check ConfigMap revisions, missing references and application logs.
6. Inspect CPU/memory pressure, quota, HPA and PDB status.
7. Determine whether a rollout, network or application regression caused the incident.

### Recovery

1. Freeze further promotion.
2. Restore the last known-good **verified digest** via an approved GitOps revert.
3. Confirm Argo CD desired/live convergence.
4. Verify ready replicas, healthy endpoints and HTTP SLIs.
5. Record time to detect, time to recover, blast radius and corrective actions.

A manual \`kubectl rollout undo\` may be used only under authorized break-glass policy; Git desired state must be reconciled promptly afterward.

## 18. Operations runbook

Create \`docs/OPERATIONS-RUNBOOK.md\`:

\`\`\`markdown
# Kubernetes Deployment and Connectivity Operations Runbook

## First checks
1. Verify cluster context and namespace.
2. Identify the approved GitOps commit and image digest.
3. Check Deployment, Pods, Service, EndpointSlices and events.
4. Check probes, resource pressure and configuration references.
5. Compare application SLIs with the pre-release baseline.

## Containment
- Pause further environment promotion.
- Preserve nonsecret evidence and event timelines.
- Do not bypass admission or security policy.
- Avoid ad hoc live-state changes in Argo CD-managed environments.

## Recovery
1. Select the last known-good retained digest.
2. Open an approved GitOps revert or emergency change.
3. Verify Argo CD reconciliation.
4. Validate ready replicas, service connectivity and error/latency SLIs.
5. Document root cause, blast radius and follow-up owners.

## Escalation
Platform: scheduling, CNI, ingress, DNS, cluster-wide incidents.
Security: secret exposure, admission bypass, compromised image.
Application: crashes, probes, dependency and application regressions.
Release owner: promotion and rollback decisions.
\`\`\`

## 19. SRE observability and acceptance metrics

| Signal | Acceptance intent |
| --- | --- |
| Available/desired replicas | Workload availability |
| Ready Service endpoints | Correct backend routing |
| Health endpoint success | Basic application readiness |
| HTTP 5xx rate | User-visible failure detection |
| p95/p99 latency | Performance regression detection |
| Pod restart and OOM rate | Stability |
| HPA desired/current replicas | Scaling health |
| PDB disruptions allowed | Maintenance readiness |
| Config change propagation | Configuration consistency |
| Argo CD sync/health | GitOps convergence |
| Rollback duration | Recovery readiness |

Use measured baselines and service objectives; do not invent a universal error-rate or latency threshold.

## 20. Acceptance scoring

| Category | Points |
| --- | ---: |
| Secure image, Deployment and probes | 15 |
| ConfigMap and secret governance | 10 |
| Service, EndpointSlices and DNS | 15 |
| Rollout and graceful recovery | 15 |
| HPA/PDB and capacity controls | 10 |
| Namespace security and isolation review | 10 |
| GitLab CI/GitOps promotion design | 10 |
| Negative tests and incident runbook | 10 |
| Evidence and reviewer sign-off | 5 |
| **Total** | **100** |

**Pass threshold:** At least **85/100** and every critical control must pass: correct context, immutable digest, restricted runtime, ready Service, verified rollback path, and no production security bypass. If an optional integration is unavailable, mark it **Not Tested**; do not award points for unexecuted checks.

## 21. Acceptance checklist

- [ ] Disposable namespace and context verified.
- [ ] Image built, scanned and referenced by real immutable digest.
- [ ] Non-root Deployment has requests, limits and probes.
- [ ] Three Pods ready behind a ClusterIP Service.
- [ ] EndpointSlices contain ready backends.
- [ ] Health and configuration endpoints verified.
- [ ] ConfigMap update and Pod restart semantics demonstrated.
- [ ] HPA/PDB inspected or prerequisite limitation recorded.
- [ ] DNS and ingress dependencies reviewed.
- [ ] Namespace security and NetworkPolicy reviewed.
- [ ] At least four negative tests completed and recovered.
- [ ] GitLab CI/GitOps ownership boundaries documented.
- [ ] Same-digest promotion model validated across four namespaces.
- [ ] SRE incident runbook and rollback reviewed.
- [ ] Reviewer signed off on risks and acceptance evidence.

## 22. Evidence worksheet

\`\`\`text
CHAPTER 030 — KUBERNETES DEPLOYMENT AND RELEASE CAPSTONE
Date:
Reviewer:
Cloud / cluster / context:
Disposable namespace:
GitLab source commit:
Image repository / verified digest:
Security scan / signature reference:
Deployment replicas desired/available:
Startup/readiness/liveness:
Runtime UID / security context:
Resource requests/limits:
ConfigMap revision / config endpoint:
Service ClusterIP / EndpointSlices:
DNS result:
Ingress/Gateway (if tested):
NetworkPolicy review:
HPA current/desired and metrics:
PDB disruptions allowed:
Negative tests performed:
Failure root causes and recovery times:
GitOps MR and Argo CD design:
Last known-good rollback digest:
Application 5xx / latency before and after:
Score / 100:
Critical controls pass/fail:
Decision: PASS / NOT READY / INCOMPLETE
Open risks / owners / due dates:
\`\`\`

## 23. Knowledge checks

1. Why must the application image digest be unchanged across environment promotion?
2. Why is Pod \`Running\` insufficient as a release success signal?
3. What makes an EndpointSlice useful during Service troubleshooting?
4. Why can changing a ConfigMap fail to update existing Pods?
5. How do HPA, resource quota and rollout surge capacity interact?
6. Which disruptions does a PDB not protect against?
7. Why does GitOps rollback require changing Git desired state?
8. Why do namespaces in one cluster share control-plane and node failure risks?
9. What distinguishes a successful Kubernetes rollout from a successful user-facing release?
10. Which evidence would an SRE require before approving production promotion?

## 24. Cleanup

Only delete resources created for the isolated lab:

\`\`\`bash
kubectl delete -f k8s/hpa.yaml --ignore-not-found
kubectl delete -f k8s/pdb.yaml --ignore-not-found
kubectl delete -f k8s/service.yaml --ignore-not-found
kubectl delete -f k8s/deployment.yaml --ignore-not-found
kubectl delete -f k8s/configmap.yaml --ignore-not-found
\`\`\`

Do not delete shared namespaces, ingress controllers, DNS, cluster metrics or other teams' resources. For GitOps-managed objects, clean up via reviewed Git changes.

## 25. Part 06 completion

Chapters 026–030 establish a practical Kubernetes deployment foundation: workloads, configuration and secrets, Service networking, health and scaling, and operational recovery.

**Next: Chapter 031 — Helm Architecture, Charts, Templates and Values Fundamentals**, beginning Part 07 — Enterprise Helm Chart Engineering.
