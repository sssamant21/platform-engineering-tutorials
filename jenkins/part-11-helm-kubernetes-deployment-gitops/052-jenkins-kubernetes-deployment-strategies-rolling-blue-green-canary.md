# Chapter 052 — Jenkins Kubernetes Deployment Strategies: Rolling, Blue-Green and Canary

**Part 11 — Helm, Kubernetes Deployment and GitOps**  
**Audience:** Jenkins SRE, release engineers, Kubernetes platform and incident response teams  
**Prerequisites:** Chapter 051; disposable Kubernetes cluster; Jenkins release identity, Helm 3, kubectl, metrics and a synthetic HTTP application.

## Objectives

Compare rolling, blue-green and canary deployments; implement safe Jenkins orchestration; define objective promotion and rollback gates; control traffic, schema compatibility and release blast radius; test recovery under failure.

## 1. Strategy comparison

| Strategy | Traffic behavior | Extra capacity | Rollback mechanism | Best fit |
|---|---|---|---|---|
| Rolling | Gradual Pod replacement within one Deployment | Depends on maxSurge | Revert Deployment revision/image | Stateless backward-compatible changes |
| Blue-green | Switch Service/Ingress from blue to green | Usually near 2× | Switch traffic selector/routing back | Fast cutover and validation |
| Canary | Small percentage of traffic to candidate | Partial additional capacity | Set canary weight to 0 | Risk-sensitive releases with telemetry |

**Critical:** A Kubernetes Deployment rolling update is built in. Blue-green and traffic-weighted canary require explicit routing and orchestration. Ordinary Kubernetes Services do **not** provide precise weighted routing. Use a supported service mesh, ingress controller or rollout controller for weighted canary; verify actual controller behavior.

## 2. Release safety prerequisites

Use immutable signed image digests, reviewed manifests, readiness probes, PodDisruptionBudgets where appropriate, capacity reservations, separate release identity, approval gates, application telemetry, and tested rollback. Treat database migrations and external side effects separately; Kubernetes rollback cannot reverse irreversible writes.

```text
Build/test/scan/sign
       ↓
Deploy candidate
       ↓
Readiness and synthetic checks
       ↓
SLO/error-budget gate
       ↓
Approval (if required)
       ↓
Traffic promotion
       ↓
Observe → accept or rollback
```

## 3. Rolling deployment

A Deployment strategy can control replacement surge and unavailability:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sample-app
  namespace: jenkins-staging
spec:
  replicas: 4
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: sample-app
  template:
    metadata:
      labels:
        app: sample-app
    spec:
      automountServiceAccountToken: false
      containers:
        - name: app
          image: registry.example.test/training/sample-app@sha256:REPLACE_WITH_REAL_DIGEST
          ports:
            - containerPort: 8080
          readinessProbe:
            httpGet: {path: /healthz, port: 8080}
            periodSeconds: 5
          resources:
            requests: {cpu: 100m, memory: 128Mi}
            limits: {cpu: 500m, memory: 512Mi}
          securityContext:
            runAsNonRoot: true
            runAsUser: 10001
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
```

Use a real image digest that runs as UID 10001 and exposes `/healthz`. A replica count of four and maxSurge one requires enough cluster capacity for five Pods. `maxUnavailable: 0` does not guarantee zero application errors; readiness, graceful shutdown, load balancing and dependencies still matter.

```sh
kubectl apply -f rolling-deployment.yaml
kubectl rollout status deployment/sample-app -n jenkins-staging --timeout=5m
kubectl rollout history deployment/sample-app -n jenkins-staging
```

Rollback requires an available prior revision:

```sh
kubectl rollout undo deployment/sample-app -n jenkins-staging
kubectl rollout status deployment/sample-app -n jenkins-staging --timeout=5m
```

If Helm manages the Deployment, prefer **Helm-managed rollback** instead of independent kubectl mutation; otherwise Helm history and live state may diverge.

## 4. Blue-green pattern

Create two Deployments with stable distinct labels, such as `app: sample-app`, `track: blue` and `track: green`. Route traffic using one Service:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: sample-app
  namespace: jenkins-staging
spec:
  selector:
    app: sample-app
    track: blue
  ports:
    - name: http
      port: 80
      targetPort: 8080
```

After the green Deployment is ready, run synthetic tests through a **preview Service** that selects `track: green`. Promote by updating the **managed source-of-truth** Service selector to `green` using Helm or GitOps. A direct `kubectl patch` is acceptable only for a controlled lab or where the Service is explicitly kubectl-managed; do not fight Helm/GitOps reconciliation.

Lab-only cutover:

```sh
kubectl patch service sample-app -n jenkins-staging \
  -p '{"spec":{"selector":{"app":"sample-app","track":"green"}}}'
kubectl get endpointslices -n jenkins-staging \
  -l kubernetes.io/service-name=sample-app
```

Service routing updates are eventually propagated; existing connections may persist on blue. Keep blue capacity available through a defined rollback window. Validate sticky sessions, long-lived requests and database compatibility.

## 5. Canary pattern

Weighted traffic shifting needs an approved ingress, service mesh or rollout controller. Example **conceptual** traffic policy:

```yaml
release:
  stableDigest: sha256:APPROVED_STABLE
  candidateDigest: sha256:APPROVED_CANDIDATE
  trafficSteps: [5, 20, 50, 100]
  analysis:
    windowMinutes: 10
    maxErrorRate: 0.01
    maxP95LatencyMs: 500
    minRequestCount: 200
```

This is a planning document, **not** a Kubernetes API manifest. Replace digest placeholders and thresholds with workload-specific measured baselines. At low traffic, 5% may yield too few requests for meaningful inference; use minimum sample sizes and manual review.

A supported implementation could use Argo Rollouts, Flagger or mesh/ingress-native routing, but choose one controller as the traffic authority. Do not manually edit routing objects that an operator continuously reconciles.

## 6. Jenkins promotion workflow

```groovy
pipeline {
    agent { label 'trusted-release' }
    parameters {
        choice(name: 'STRATEGY', choices: ['rolling', 'blue-green', 'canary'])
        string(name: 'IMAGE_DIGEST', defaultValue: '', description: 'Approved sha256 digest')
    }
    options {
        timestamps()
        timeout(time: 45, unit: 'MINUTES')
        disableConcurrentBuilds()
    }
    stages {
        stage('Validate') {
            steps {
                sh '''#!/bin/sh
                    set -eu
                    printf '%s' "$IMAGE_DIGEST" | grep -Eq '^sha256:[a-f0-9]{64}$'
                    helm lint charts/sample-app -f environments/staging-values.yaml
                '''
            }
        }
        stage('Approve') {
            steps {
                input message: 'Approve staging release strategy and digest?', ok: 'Proceed'
            }
        }
        stage('Execute strategy') {
            steps {
                script {
                    if (params.STRATEGY == 'rolling') {
                        sh '''#!/bin/sh
                            set -eu
                            helm upgrade --install sample-app charts/sample-app \
                              -n jenkins-staging \
                              -f environments/staging-values.yaml \
                              --set-string image.digest="$IMAGE_DIGEST" \
                              --atomic --wait --timeout 10m
                        '''
                    } else {
                        error("Strategy requires its approved routing controller and separate implementation: " + params.STRATEGY)
                    }
                }
            }
        }
        stage('Verify') {
            steps {
                sh 'kubectl rollout status deployment/sample-app -n jenkins-staging --timeout=5m'
            }
        }
    }
}
```

This Pipeline **intentionally refuses** blue-green and canary until a tested routing implementation exists; it does not falsely claim to implement weighted routing. For a production-ready pipeline, add image signature verification, policy gates, SLO queries, external synthetic checks, change ticket, deployment evidence and automatic halt/rollback logic.

## 7. SLO-driven promotion gates

Measure at least error rate, p95/p99 latency, saturation, request volume, availability and business-critical synthetic transactions. Compare candidate and stable cohorts using consistent labels and time windows. Fail closed if metrics are unavailable, the sample is insufficient, or the query is stale. Define an explicit maximum exposure time and escalation path.

```text
Candidate ready?
  no → rollback
  yes → enough requests?
           no → hold / manual decision
           yes → SLO within approved threshold?
                    no → rollback
                    yes → next traffic step
```

## 8. Database and state compatibility

Use expand/contract schema changes. Deploy additive schema first, then compatible app, then remove old schema only after rollback window closes. Feature flags should support quick disablement. For irreversible migrations, have a restore/forward-fix plan and business-approved RPO/RTO. Blue-green does not isolate shared databases automatically.

## 9. Capacity and cost

Rolling with `maxSurge` needs transient spare capacity. Blue-green may nearly double app footprint. Canary adds candidate capacity and metrics overhead. Account for cluster autoscaler lead time, PDBs, quotas, image pull latency, ingress/mesh cost and artifact retention. A strategy that cannot schedule candidate Pods is not safe to promote.

## 10. Troubleshooting matrix

| Failure | Evidence | Recovery |
|---|---|---|
| Rolling stuck | Deployment conditions/events | Fix readiness/capacity |
| MaxSurge Pending | Scheduler events | Add capacity |
| Readiness false | Pod logs/probes | Fix application |
| Blue-green wrong selector | Service/EndpointSlices | Restore prior selector |
| Green not ready | Green Deployment | Hold cutover |
| Existing connections stay blue | Ingress/connection telemetry | Drain carefully |
| Canary weight ineffective | Controller routing status | Fix routing authority |
| Low canary traffic | Request counts | Extend observation |
| SLO regression | Error/latency metrics | Shift weight to stable |
| Metrics unavailable | Monitoring errors | Fail closed |
| Session incompatibility | Synthetic tests | Roll back/mitigate |
| Database migration breaks rollback | Schema version | Forward fix/restore plan |
| Helm/GitOps drift | Reconciliation logs | One owner |
| Registry digest missing | Image pull events | Restore approved digest |
| Rollback revision missing | Helm/Deployment history | Redeploy verified manifest |
| Pod quota exceeded | ResourceQuota | Adjust capacity |

## 11. Production runbooks

### A. Rolling rollout
1. Confirm digest/signature, chart, quota and spare capacity.
2. Deploy through one controller (Helm or GitOps).
3. Observe readiness, rollout and error budget.
4. Roll back through the same controller on failure.
5. Preserve evidence and close change.

### B. Blue-green cutover
1. Deploy green separately, test via preview Service.
2. Validate schema, sessions, readiness and synthetic transactions.
3. Obtain approval and switch the managed routing source.
4. Monitor real traffic; retain blue for rollback.
5. Decommission blue only after approved observation window.

### C. Canary promotion
1. Verify controller and routing policies.
2. Start at small weight, check minimum request count.
3. Compare candidate/stable SLOs and pause if inconclusive.
4. Promote stepwise or shift to stable on regression.
5. Preserve weights, metrics and approval evidence.

### D. Bad release incident
1. Halt promotion and identify deployed digest/chart revision.
2. Restore traffic to stable or roll back via owning controller.
3. Check downstream effects, schema and queues.
4. Confirm SLO recovery and customer impact.
5. Document RCA and corrective action.

### E. Drift/ownership conflict
1. Identify Helm, Argo CD, Flux or rollout controller as owner.
2. Capture Git desired state and live routing.
3. Stop competing mutations through change control.
4. Reconcile one authoritative source.
5. Validate no recurring drift.

## 12. Acceptance criteria

- [ ] Rolling deployment and rollback tested.
- [ ] Blue-green preview and selector cutover demonstrated.
- [ ] Canary controller selected and weighted routing validated if available.
- [ ] SLO gates fail closed on missing metrics.
- [ ] Immutable digest and release evidence preserved.
- [ ] Database rollback compatibility reviewed.
- [ ] Spare capacity and autoscaler latency measured.
- [ ] Helm/GitOps/routing ownership documented.

**Companion:** [Chapter 052 hands-on lab](labs/052-jenkins-kubernetes-deployment-strategies-rolling-blue-green-canary-check.md).  
**Next:** Chapter 053 — Jenkins Integration with Argo CD and Flux GitOps.
