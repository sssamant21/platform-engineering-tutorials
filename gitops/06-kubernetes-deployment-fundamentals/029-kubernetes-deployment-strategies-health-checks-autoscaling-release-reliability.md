# Chapter 029 — Kubernetes Deployment Strategies, Health Checks, Autoscaling and Release Reliability

**Part 06 — Kubernetes Deployment Fundamentals** | **Chapter 029 / 100**  
**Audience:** SRE, Kubernetes administrators, infrastructure and platform engineers  
**Toolchain:** Kubernetes, kubectl, GitLab CI, Helm and Argo CD  
**Environment model:** One shared Kubernetes cluster with separate \`demo-dev\`, \`demo-test\`, \`demo-staging\` and \`demo-prod\` namespaces.

> **Safety:** Execute failure injection only in an approved disposable namespace. All examples use generic names and require an actual authorized image digest. Manual \`kubectl\` changes are for isolated labs; GitOps-managed environments must be updated through approved desired-state changes.

## 1. Learning objectives

1. Compare RollingUpdate, Recreate, blue/green and canary deployment patterns.
2. Explain readiness, liveness and startup probes, including failure interactions.
3. Configure \`maxSurge\`, \`maxUnavailable\`, \`minReadySeconds\` and \`progressDeadlineSeconds\`.
4. Describe Horizontal Pod Autoscaler (HPA) and its metrics prerequisites.
5. Understand PodDisruptionBudgets (PDBs), graceful shutdown and node drain behavior.
6. Diagnose stuck rollouts, readiness failures, resource pressure and scaling oscillations.
7. Separate GitLab CI artifact creation from Argo CD release reconciliation.
8. Demonstrate safe release rollback and post-deployment SLO validation.
9. Build an SRE release-readiness checklist for EKS, AKS and GKE.

## 2. Release reliability architecture

\`\`\`text
GitLab merge request -> tests / scans / SBOM / provenance
                                |
                   trusted build -> OCI image@sha256:DIGEST
                                |
                    reviewed GitOps digest change
                                |
                         Argo CD Application
                                |
                     Deployment controller
                                |
                   ReplicaSet A -> ReplicaSet B
                         |            |
                    ready Pods     new ready Pods
                         +-----Service----+
                                |
                          application SLOs
                                |
                   HPA / PDB / probes / metrics
\`\`\`

GitOps promotion should preserve the same immutable digest across Dev, Test, Staging and Production. Configuration can differ by namespace. Namespaces do not provide independent control planes or eliminate cluster-wide failure domains.

## 3. Deployment strategies

| Strategy | How it works | Strength | Operational risk |
| --- | --- | --- | --- |
| RollingUpdate | Gradually replace Pods | Built-in, incremental | Requires surge capacity and healthy readiness |
| Recreate | Stop old Pods before new | Simple, avoids version overlap | Usually causes downtime |
| Blue/green | Keep two release environments, switch traffic | Fast cutover/rollback | Extra capacity and careful data compatibility |
| Canary | Shift limited traffic to new version | Reduced blast radius | Needs traffic control and observability |
| Progressive delivery | Automated traffic and metric gates | Controlled risk | Additional controllers and policy complexity |

Kubernetes Deployment natively supports **RollingUpdate** and **Recreate**. Blue/green and weighted canary traffic require additional routing/controller mechanisms; Argo Rollouts is introduced in later chapters. Two ReplicaSets coexisting during a rolling update do not automatically constitute a weighted canary.

## 4. RollingUpdate mathematics

For a Deployment with \`replicas: 4\`:

\`\`\`yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
\`\`\`

The controller may run up to **5** Pods during rollout and aims to keep at least **4 available**. Scheduling capacity, quotas, image pulls, probes and Pod termination can prevent the desired progression.

Percentage values are rounded according to Kubernetes Deployment semantics: \`maxSurge\` rounds up; \`maxUnavailable\` rounds down. Always evaluate the effective values at small replica counts.

\`minReadySeconds\` specifies how long a newly ready Pod must remain ready before counting as available. \`progressDeadlineSeconds\` sets the window after which Kubernetes reports rollout progress failure; it does **not** automatically roll back a Deployment.

## 5. Health probes

| Probe | Purpose | Failure result |
| --- | --- | --- |
| Startup | Allow initialization time | Repeated failure eventually restarts container |
| Readiness | Decide whether Pod should receive normal Service traffic | Pod removed from ready endpoints |
| Liveness | Detect stuck/unrecoverable process | Container restarted after threshold |

Design principles:

- Readiness should indicate ability to serve traffic, including truly required dependencies.
- Liveness should avoid fragile downstream checks that cause restart storms during shared dependency incidents.
- Startup probes protect slow-starting applications from premature liveness/readiness failures.
- Timeouts and thresholds should reflect measured startup and recovery behavior.
- Probe success is not proof that user-facing latency/error SLOs are satisfied.

## 6. Lab prerequisites

- Approved disposable \`demo-dev\` namespace.
- A real, accessible immutable OCI image digest for a sample HTTP service listening on port 8080 with \`/healthz\`.
- Permissions to manage Deployment, Service and optional HPA/PDB.
- Metrics Server or compatible metrics API for CPU-based HPA.
- Sufficient namespace quota for surge capacity.
- \`kubectl\` configured for the intended cluster.

Verify:

\`\`\`bash
kubectl config current-context
kubectl auth can-i create deployments -n demo-dev
kubectl auth can-i create horizontalpodautoscalers -n demo-dev
kubectl auth can-i create poddisruptionbudgets -n demo-dev
kubectl top nodes
\`\`\`

If \`kubectl top\` fails because metrics are unavailable, complete the manual rollout lab and treat HPA testing as blocked until metrics are configured.

## 7. Lab A — Production-style Deployment manifest

Create \`k8s/deployment.yaml\`:

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
  minReadySeconds: 10
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
      terminationGracePeriodSeconds: 30
      automountServiceAccountToken: false
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
            failureThreshold: 2
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            periodSeconds: 10
            timeoutSeconds: 2
            failureThreshold: 3
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

Replace the image placeholder with a real approved digest. The lab image must be compatible with non-root/read-only execution.

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
    app: demo-app
  ports:
    - name: http
      port: 80
      targetPort: http
\`\`\`

Validate and apply:

\`\`\`bash
kubectl apply --dry-run=server -f k8s/deployment.yaml
kubectl apply --dry-run=server -f k8s/service.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl rollout status deployment/demo-app -n demo-dev --timeout=240s
kubectl get deployment,replicaset,pods,service -n demo-dev -o wide
\`\`\`

Expected: 3 available replicas. The rollout can take longer than a simple probe pass because \`minReadySeconds: 10\` delays availability accounting.

## 8. Lab B — Observe a rolling update

For a meaningful image rollout, use a **second approved digest** that has passed build, scan, signing and verification gates. Modify only the image digest in a copy of the manifest and apply it in \`demo-dev\`.

Watch:

\`\`\`bash
kubectl get pods -n demo-dev -l app=demo-app -w
kubectl rollout status deployment/demo-app -n demo-dev --timeout=240s
kubectl rollout history deployment/demo-app -n demo-dev
kubectl describe deployment demo-app -n demo-dev
\`\`\`

Expected: old and new ReplicaSets temporarily coexist, surge capacity is used if available, and new Pods become available before old ones are removed.

Record both digests, the rollout duration, ready replica count and any transient 5xx errors.

## 9. Lab C — Graceful shutdown and readiness

Kubernetes sends termination signals and allows a grace period; the application must actually handle termination and drain traffic correctly. A \`terminationGracePeriodSeconds\` value alone does not guarantee zero dropped requests.

For HTTP servers, design shutdown to:

1. Stop accepting new work or mark readiness false.
2. Allow routing endpoints and upstream load balancers time to converge.
3. Complete in-flight requests within a bounded period.
4. Exit before the termination grace period expires.

A \`preStop\` sleep is not a universal solution and consumes the termination grace period. Test real request draining under load.

Inspect:

\`\`\`bash
kubectl describe pod -n demo-dev -l app=demo-app
kubectl get endpointslices -n demo-dev -l kubernetes.io/service-name=demo-app
\`\`\`

During a controlled Pod deletion in a disposable environment, observe endpoint readiness and client errors. Do not infer graceful shutdown from a successful \`kubectl delete\` alone.

## 10. Lab D — Horizontal Pod Autoscaler

Create \`k8s/hpa.yaml\`:

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

CPU utilization is calculated relative to container **CPU requests**, not CPU limits. Metrics availability, sufficient load, quota and schedulable capacity are required for scaling.

Apply only when the metrics API is healthy:

\`\`\`bash
kubectl apply --dry-run=server -f k8s/hpa.yaml
kubectl apply -f k8s/hpa.yaml
kubectl describe hpa demo-app -n demo-dev
kubectl get hpa demo-app -n demo-dev -w
kubectl top pods -n demo-dev
\`\`\`

Expected: the HPA reports current/target CPU utilization once metrics are available. It may not scale without sustained CPU demand. Do not generate unbounded load against shared nodes.

**GitOps warning:** When HPA controls replicas, avoid repeated drift from an independently managed \`spec.replicas\` field. Configure chart and Argo CD ownership carefully so the HPA and GitOps reconciliation do not fight.

## 11. Lab E — PodDisruptionBudget

Create \`k8s/pdb.yaml\`:

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

Apply:

\`\`\`bash
kubectl apply --dry-run=server -f k8s/pdb.yaml
kubectl apply -f k8s/pdb.yaml
kubectl get pdb demo-app -n demo-dev
kubectl describe pdb demo-app -n demo-dev
\`\`\`

A PDB governs certain **voluntary evictions** (for example, node drain using the Eviction API); it does not prevent involuntary node failures or guarantee a Deployment rollout has no disruption. PDB configuration must be compatible with replica count, readiness and maintenance procedures.

Do not drain a shared cluster node as part of this lab.

## 12. Scaling and reliability interactions

| Condition | Consequence | Mitigation |
| --- | --- | --- |
| HPA requests more replicas than quota permits | Pending/admission failures | Capacity and quota planning |
| Surge Pods cannot schedule | Rollout stalls | Reserve headroom |
| Aggressive liveness probe | Restart loops | Probe tuning |
| Readiness depends on flaky external service | Broad endpoint loss | Separate critical vs optional dependencies |
| PDB too strict | Node maintenance blocked | Match PDB to replica capacity |
| HPA and GitOps both own replicas | Continuous drift | Clarify field ownership |
| No zone spread | Replicas may share failure domain | Topology spread/affinity |
| Missing metrics | HPA cannot calculate desired scale | Repair metrics pipeline |

## 13. Optional topology spread

For production-like reliability, distribute replicas across available zones/nodes when the cluster topology supports it.

Example fragment:

\`\`\`yaml
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: ScheduleAnyway
    labelSelector:
      matchLabels:
        app: demo-app
\`\`\`

\`ScheduleAnyway\` is a preference, not a hard guarantee of multi-zone placement. A cluster with one zone cannot deliver multi-zone fault tolerance.

## 14. Failure-injection exercises

Perform only in \`demo-dev\`.

### Test A — Broken readiness

Change readiness path from \`/healthz\` to \`/missing\`.

Expected: new Pods remain unready; rollout stalls; existing ready Pods may continue serving.

Recover by restoring the probe path and reapplying the approved manifest.

### Test B — Broken liveness

Change liveness path to \`/missing\` in a disposable revision.

Expected: containers repeatedly restart after startup and liveness thresholds. Inspect restart counts and events.

Recover by restoring the correct path. Avoid using liveness checks that depend on optional downstream services.

### Test C — Unavailable image

Use a nonexistent image digest in a disposable revision.

Expected: \`ImagePullBackOff\` and rollout failure; prior ready replicas may remain serving with \`maxUnavailable: 0\`.

Recover by restoring the previously verified digest.

### Test D — Insufficient surge capacity

In a disposable namespace, lower quota or increase requests so surge Pods cannot schedule.

Expected: rollout stalls with quota or scheduling events. Restore capacity and resource requests after the test.

### Test E — Missing HPA metrics

Temporarily test in a disposable environment without metrics availability, or inspect an existing HPA with unknown metrics.

Expected: HPA cannot calculate the desired replica count reliably. Do not disable shared Metrics Server.

### Test F — PDB blocks eviction

Review \`kubectl describe pdb\` and the \`DisruptionsAllowed\` value. Do **not** drain a shared node. If using a dedicated disposable node pool, conduct an authorized maintenance drill with rollback prepared.

## 15. Troubleshooting commands

\`\`\`bash
kubectl get deployment,replicaset,pods,hpa,pdb -n demo-dev
kubectl describe deployment demo-app -n demo-dev
kubectl rollout status deployment/demo-app -n demo-dev --timeout=120s
kubectl rollout history deployment/demo-app -n demo-dev
kubectl describe hpa demo-app -n demo-dev
kubectl describe pdb demo-app -n demo-dev
kubectl get events -n demo-dev --sort-by=.lastTimestamp
kubectl logs -n demo-dev deployment/demo-app --tail=100
kubectl top pods -n demo-dev
\`\`\`

If metrics are unavailable, investigate the metrics API rather than assuming the application is idle.

## 16. GitLab CI, Helm and Argo CD release controls

GitLab CI should validate:

- Manifest and Helm template syntax.
- Resource requests/limits and probe definitions.
- Image digest pinning and signature/provenance.
- Rollout strategy and environment-specific constraints.
- Policy compliance and approved promotion rules.

Argo CD should reconcile the reviewed desired state. For production, use approval gates, sync windows and/or manual sync policy as appropriate. A CI job should not directly mutate production Deployments merely because its tests passed.

Example Helm values:

\`\`\`yaml
replicaCount: 3
image:
  repository: registry.example.com/training/demo-app
  digest: sha256:REPLACE_WITH_REAL_DIGEST
deployment:
  maxSurge: 1
  maxUnavailable: 0
  minReadySeconds: 10
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 6
  cpuUtilization: 70
\`\`\`

A production chart should omit or appropriately manage \`spec.replicas\` when HPA is enabled. Do not paste this values fragment into an unrelated chart without checking its schema.

## 17. SRE incident runbook

**Scenario:** A new release reports healthy Pods but increased HTTP 5xx and p99 latency.

1. Identify release commit, image digest, namespace and rollout start time.
2. Compare user-facing SLIs before and after deployment.
3. Inspect readiness/liveness/startup failures and restart counts.
4. Check new vs old ReplicaSets, resource pressure and Pod placement.
5. Inspect Service EndpointSlices, ingress/controller metrics and dependencies.
6. Review HPA decisions, CPU/memory saturation and quota headroom.
7. Stop further environment promotion.
8. Revert the GitOps digest to the retained, verified known-good image if release regression is confirmed.
9. Validate Argo CD sync, Deployment availability, error rate and latency recovery.
10. Document timeline, root cause, corrective actions and rollback readiness.

**Manual \`kubectl rollout undo\`** is a break-glass action only when authorized; Argo CD may restore Git desired state unless Git is updated.

## 18. SRE observability and release acceptance

Track:

- Deployment available/desired replica ratio and rollout duration.
- Pod readiness, restarts, OOMKills and scheduling failures.
- HPA current/desired replicas and CPU utilization.
- PDB disruptions allowed and blocked evictions.
- HTTP success rate, p95/p99 latency and traffic volume.
- Service ready endpoints and ingress backend health.
- GitOps sync/health conditions and drift.
- Registry pull failures and admission policy denials.

Use real baselines and error budgets. Do not claim release success from Kubernetes rollout status alone.

## 19. Cleanup

Only remove resources created in your disposable lab:

\`\`\`bash
kubectl delete -f k8s/hpa.yaml --ignore-not-found
kubectl delete -f k8s/pdb.yaml --ignore-not-found
kubectl delete -f k8s/service.yaml --ignore-not-found
kubectl delete -f k8s/deployment.yaml --ignore-not-found
\`\`\`

Do not delete shared namespaces or other teams' resources. For Argo CD-managed workloads, perform cleanup through a reviewed GitOps change.

## 20. Acceptance checklist

- [ ] Correct context and disposable namespace confirmed.
- [ ] Deployment uses an actual verified image digest.
- [ ] Three replicas become available behind a Service.
- [ ] RollingUpdate surge/unavailability behavior observed.
- [ ] Startup, readiness and liveness probes validated.
- [ ] \`minReadySeconds\` and progress deadline understood.
- [ ] HPA created and metrics status verified, or prerequisite documented.
- [ ] PDB created and disruptions-allowed state inspected.
- [ ] Readiness and image-pull failures diagnosed and recovered.
- [ ] Resource headroom and scheduling risks documented.
- [ ] GitOps rollback path and SLO acceptance criteria reviewed.
- [ ] No unauthorized production changes made.

## 21. Evidence worksheet

\`\`\`text
CHAPTER 029 — DEPLOYMENT STRATEGIES AND RELEASE RELIABILITY
Date:
Cluster/context:
Namespace:
Source commit:
Original image digest:
New image digest:
Desired/available replicas:
maxSurge/maxUnavailable:
minReadySeconds:
Progress deadline:
Rollout duration:
Startup/readiness/liveness results:
HPA min/max/current/desired:
CPU metrics availability:
PDB minAvailable/disruptionsAllowed:
Zone/node placement:
Failure injections and recovery:
Service error rate and latency:
GitOps MR / Argo CD status:
Rollback digest and verification:
Reviewer:
Open risks and owners:
\`\`\`

## 22. Knowledge checks

1. What distinguishes RollingUpdate from Recreate?
2. Why is a Kubernetes rolling update not automatically a weighted canary?
3. What does \`progressDeadlineSeconds\` do, and what does it not do?
4. Why can a Pod be Running but not available?
5. How does CPU-based HPA use requests rather than limits?
6. What disruptions are and are not protected by a PDB?
7. Why can HPA and GitOps disagree over \`spec.replicas\`?
8. Why must application SLOs be checked after a successful rollout?

## 23. Completion

**Pass:** The operator demonstrates a safe rolling update, validates probes and Service readiness, inspects autoscaling and disruption policy, and recovers from a broken release through the approved desired-state workflow.

**Next: Chapter 030 — Kubernetes Deployment, Connectivity and Release Reliability Capstone**, completing Part 06.
