# Chapter 062 — Container Startup and Image Pull Failures

**Track:** Kubernetes Administration · **Part 13 — Troubleshooting and Incident Response**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, application and platform engineers  
**Prerequisites:** Chapter 061, kubectl, Windows PowerShell, an approved staging cluster, permissions to inspect Pods and Events

## 1. Production scenario

A production Deployment rollout stalls. Some replacement Pods report \`ImagePullBackOff\`, others \`CreateContainerConfigError\`, and a third set briefly starts before restarting. The application has fewer Ready replicas and HTTP errors rise. The team needs to identify distinct failure modes before changing image tags, Secrets, ServiceAccounts or application configuration.

**Goal:** diagnose the complete container startup path—from scheduling and image resolution through runtime creation, process execution and readiness—and recover safely without masking the evidence or introducing unreviewed production changes.

### Learning objectives

1. Explain Pod scheduling, image pulling, container configuration, runtime startup and probe transitions.
2. Distinguish \`ErrImagePull\`, \`ImagePullBackOff\`, \`CreateContainerConfigError\`, \`CreateContainerError\`, \`RunContainerError\` and \`CrashLoopBackOff\`.
3. Diagnose registry authorization, DNS, TLS, image architecture, tags, digests and pull policy.
4. Troubleshoot ConfigMaps, Secrets, ServiceAccounts, security contexts, volumes and commands.
5. Collect Events, current/previous logs, container state and rollout history safely.
6. Test representative failures in an isolated namespace.
7. Build an incident runbook with safe rollback, validation and prevention controls.

## 2. Container startup lifecycle

\`\`\`text
Deployment/Job/StatefulSet controller
              |
         Pod created
              |
       Scheduler assigns node
              |
    Kubelet resolves image reference
              |
  Registry auth / DNS / TLS / image pull
              |
  Container config / volumes / sandbox
              |
   OCI runtime creates and starts process
              |
     Startup / readiness / liveness
              |
        Ready application endpoint
\`\`\`

A Pod can be **Pending** while images are downloading or container setup is incomplete. A container waiting reason provides more detail than the Pod phase alone. \`Running\` does not guarantee \`Ready\`.

### Failure classification

| Symptom | Stage | Common causes |
|---|---|---|
| \`ErrImagePull\` | Image retrieval | Missing image/tag, registry authentication, network/TLS |
| \`ImagePullBackOff\` | Retrying pull | Earlier pull failed; retry backoff |
| \`InvalidImageName\` | Image reference | Malformed image name |
| \`CreateContainerConfigError\` | Configuration | Missing Secret/ConfigMap key, invalid environment reference |
| \`CreateContainerError\` | Container creation | Runtime, mounts, permissions or invalid creation settings |
| \`RunContainerError\` | Process start | Invalid command, executable or runtime startup failure |
| \`CrashLoopBackOff\` | Repeated process failure | Exit, startup failure, probe-triggered restart |
| \`ContainerCreating\` | Setup in progress | Image pull, CNI, sandbox or volume preparation |
| \`Pending\` | Pod not yet running | Scheduling, volume, image or setup delay |

**Interpretation rule:** these are symptoms or status reasons. Confirm the actual cause through Events, container state, logs and infrastructure telemetry.

## 3. Production safety and evidence preservation

Start read-only. Before deleting Pods, patching a Deployment or changing registry credentials, record:

- Cluster/context, namespace, owner, Pod UID, node, zone and revision.
- Image reference and digest, pull policy and ServiceAccount name.
- Container waiting reason, last termination reason and exit code.
- Recent Events, current/previous logs and rollout history.
- Registry errors and node-level DNS/TLS/network evidence.
- Ready replicas, EndpointSlices and customer-facing error rate.

Do **not** print Secret values into tickets, shell transcripts or shared logs. Do not change production image tags to \`latest\` as a shortcut. Use reviewed immutable digests where possible. Avoid force deleting stateful workloads.

\`\`\`powershell
kubectl config current-context
kubectl version
kubectl get nodes -o wide
kubectl auth can-i get pods -A
kubectl auth can-i get pods/log -n default
kubectl auth can-i list events -A
Get-Date -Format o
\`\`\`

## 4. Lab 1 — Identify the failing startup stage

Select an authorized namespace and Pod:

\`\`\`powershell
$ns = 'REPLACE_WITH_NAMESPACE'
$pod = 'REPLACE_WITH_POD'
kubectl -n $ns get pod $pod -o wide
kubectl -n $ns describe pod $pod
kubectl -n $ns get pod $pod -o jsonpath='{range .status.containerStatuses[*]}{.name}{" waiting="}{.state.waiting.reason}{" message="}{.state.waiting.message}{" restarts="}{.restartCount}{" lastExit="}{.lastState.terminated.exitCode}{"\n"}{end}'
kubectl -n $ns get events --sort-by=.lastTimestamp
\`\`\`

**Expected:** a waiting reason, Event message or last termination state narrows the failing stage. Container statuses may be absent before initial container creation; use \`describe pod\` and Events when JSONPath is empty.

### Decision tree

1. **Pod unscheduled?** Inspect \`FailedScheduling\`, resource requests, taints, topology and PVCs.
2. **Image pull failed?** Inspect image reference, credentials, registry response, DNS/TLS and rate limits.
3. **Container config failed?** Check Secret/ConfigMap references, keys, volume definitions and ServiceAccount.
4. **Runtime creation failed?** Check CNI, mounts, permissions, security context and node runtime.
5. **Process starts then exits?** Inspect logs, command, exit code and dependencies.
6. **Process runs but not Ready?** Inspect readiness/startup probes and Service endpoints.

## 5. Lab 2 — Diagnose image reference and pull policy

\`\`\`powershell
kubectl -n $ns get pod $pod -o jsonpath='{range .spec.containers[*]}{.name}{" image="}{.image}{" pullPolicy="}{.imagePullPolicy}{"\n"}{end}'
kubectl -n $ns get pod $pod -o jsonpath='{range .status.containerStatuses[*]}{.name}{" imageID="}{.imageID}{"\n"}{end}'
kubectl -n $ns describe pod $pod
\`\`\`

### Image reference anatomy

\`\`\`text
registry.example.com/team/api:1.2.3
registry.example.com/team/api@sha256:<digest>
\`\`\`

- A **tag** is mutable unless the registry enforces immutability.
- A **digest** identifies image content and improves reproducibility.
- \`imagePullPolicy: Always\` requests image resolution each start; cached layers may still be reused.
- \`IfNotPresent\` permits using a locally cached image.
- Kubernetes defaults pull policy based on image reference when the object is created; changing the image later does not necessarily recalculate the stored policy.

### Failure patterns

| Error clue | Likely investigation |
|---|---|
| \`manifest unknown\` / \`not found\` | Repository, tag or digest |
| \`unauthorized\` / \`denied\` | Pull credentials, registry permissions |
| \`429 Too Many Requests\` | Registry throttling / rate limit |
| \`no matching manifest\` | CPU architecture / OS mismatch |
| \`x509\` | Certificate chain / trust / expiry |
| DNS lookup error | Node DNS, proxy, VPC resolver |
| Connection timeout | Egress, firewall, proxy, private endpoint |
| \`InvalidImageName\` | Malformed reference |

**Expected:** classify the error before deciding on remediation.

## 6. Lab 3 — Inspect imagePullSecrets and ServiceAccounts safely

\`\`\`powershell
kubectl -n $ns get pod $pod -o jsonpath='{.spec.serviceAccountName}{"\n"}'
kubectl -n $ns get pod $pod -o jsonpath='{range .spec.imagePullSecrets[*]}{.name}{"\n"}{end}'
kubectl -n $ns get serviceaccounts
kubectl -n $ns describe serviceaccount REPLACE_WITH_SERVICEACCOUNT
kubectl -n $ns get secrets
\`\`\`

**Expected:** confirm the Pod or ServiceAccount references the intended image pull Secret and that the Secret exists in the **same namespace as the Pod**. Do not dump \`kubernetes.io/dockerconfigjson\` values.

### Private registry checklist

1. Is the repository path and tag/digest correct?
2. Does the image pull Secret exist in the workload namespace?
3. Is it referenced by the Pod or ServiceAccount?
4. Are credentials valid and scoped to the repository?
5. Does the node have egress and DNS connectivity to registry endpoints?
6. Is the registry certificate chain trusted by the node runtime?
7. Are cloud-provider identity mechanisms (for example ECR/ACR integration) configured correctly?

**Important:** Pod workload identity and node/image-pull identity may use different credential paths. An application's ability to call cloud APIs does not prove the node can pull a private image.

## 7. Lab 4 — Reproduce a missing image in staging

**Approved staging only.** Save \`ch062-image-failure.yaml\`:

\`\`\`yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch062
---
apiVersion: v1
kind: Pod
metadata:
  name: bad-image
  namespace: ch062
  labels:
    app: ch062-bad-image
spec:
  restartPolicy: Never
  containers:
    - name: demo
      image: registry.k8s.io/pause:ch062-nonexistent-tag
      imagePullPolicy: Always
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
        limits:
          cpu: 100m
          memory: 64Mi
\`\`\`

\`\`\`powershell
kubectl apply -f .\\ch062-image-failure.yaml
kubectl -n ch062 get pod bad-image -o wide
kubectl -n ch062 describe pod bad-image
kubectl -n ch062 get events --sort-by=.lastTimestamp
\`\`\`

**Expected:** image pull failure and eventually \`ImagePullBackOff\`, provided registry access and image resolution proceed far enough to report the nonexistent tag. If the cluster cannot reach the registry, a network error may appear first.

### Evidence

Record Pod status, Event reason/message, retry behavior and whether other Pods are healthy. Do not repeatedly delete/recreate the Pod just to reset backoff.

## 8. Lab 5 — Reproduce a missing ConfigMap key

Save \`ch062-config-failure.yaml\`:

\`\`\`yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: demo-config
  namespace: ch062
data:
  EXISTING_KEY: "present"
---
apiVersion: v1
kind: Pod
metadata:
  name: bad-config
  namespace: ch062
spec:
  restartPolicy: Never
  containers:
    - name: demo
      image: busybox:1.36
      command: ["/bin/sh", "-c", "echo started; sleep 60"]
      env:
        - name: REQUIRED_SETTING
          valueFrom:
            configMapKeyRef:
              name: demo-config
              key: MISSING_KEY
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
\`\`\`

\`\`\`powershell
kubectl apply -f .\\ch062-config-failure.yaml
kubectl -n ch062 get pod bad-config
kubectl -n ch062 describe pod bad-config
kubectl -n ch062 get configmap demo-config -o jsonpath='{.data}'
\`\`\`

**Expected:** \`CreateContainerConfigError\` and an Event identifying the missing key. The ConfigMap in this lab contains no secrets. For real production ConfigMaps, avoid displaying confidential values.

### Controlled repair (staging only)

\`\`\`powershell
kubectl -n ch062 patch configmap demo-config --type merge -p '{"data":{"MISSING_KEY":"repaired"}}'
kubectl -n ch062 get pod bad-config -w
\`\`\`

**Expected:** kubelet eventually retries container creation; the Pod starts when the required key becomes available. Exit the watch with Ctrl+C. If the Pod has already completed, no additional restart is expected because \`restartPolicy: Never\`.

## 9. Lab 6 — Reproduce an invalid startup command

Save \`ch062-command-failure.yaml\`:

\`\`\`yaml
apiVersion: v1
kind: Pod
metadata:
  name: bad-command
  namespace: ch062
spec:
  restartPolicy: Always
  containers:
    - name: demo
      image: busybox:1.36
      command: ["/definitely-not-an-executable"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
\`\`\`

\`\`\`powershell
kubectl apply -f .\\ch062-command-failure.yaml
kubectl -n ch062 get pod bad-command
kubectl -n ch062 describe pod bad-command
kubectl -n ch062 logs bad-command --previous --tail=30
kubectl -n ch062 get events --sort-by=.lastTimestamp
\`\`\`

**Expected:** runtime start failure and retry/backoff behavior. Because the executable cannot start, application logs may be empty and \`--previous\` may return an error. Use kubelet Events and container state rather than assuming an empty log means no failure.

### Common command/entrypoint problems

- Wrong \`command\` or \`args\` overrides image ENTRYPOINT/CMD.
- Missing binary or wrong path.
- Missing execute permission.
- Incompatible executable architecture or interpreter.
- Shell syntax assumed when no shell is invoked.
- Working directory, filesystem or read-only root filesystem mismatch.

## 10. Lab 7 — Differentiate startup probes and crash loops

Review an authorized application Pod:

\`\`\`powershell
kubectl -n $ns describe pod $pod
kubectl -n $ns logs $pod --all-containers=true --timestamps --since=15m --tail=100
kubectl -n $ns logs $pod --all-containers=true --previous --timestamps --tail=100
\`\`\`

### Probe responsibilities

| Probe | Purpose | Failure consequence |
|---|---|---|
| Startup | Allows slow initialization before liveness/readiness checks | After threshold, container restart |
| Readiness | Controls eligibility for Service traffic | Endpoint removed/not added |
| Liveness | Detects unhealthy running container | Container restart |

**Important:** a readiness failure alone does not restart the container. Liveness/startup failures can trigger restarts. A process exit can also cause restarts according to restart policy.

### Example startup probe

\`\`\`yaml
startupProbe:
  httpGet:
    path: /health/startup
    port: 8080
  periodSeconds: 5
  failureThreshold: 24
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  periodSeconds: 5
livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  periodSeconds: 10
\`\`\`

These are illustrative endpoints and thresholds. Do not copy them without validating the application's startup characteristics and dependency behavior.

## 11. Lab 8 — Inspect rollout health and select safe remediation

\`\`\`powershell
kubectl -n $ns get deployments,replicasets,pods -o wide
kubectl -n $ns rollout history deployment/REPLACE_WITH_DEPLOYMENT
kubectl -n $ns describe deployment REPLACE_WITH_DEPLOYMENT
kubectl -n $ns get events --sort-by=.lastTimestamp
kubectl -n $ns get endpointslices
\`\`\`

### Remediation matrix

| Confirmed issue | Safer corrective action | Verification |
|---|---|---|
| Missing tag/digest | Deploy approved existing immutable image | ImageID, Ready replicas |
| Registry auth denied | Repair scoped pull credential/identity | Pull success, audit |
| Registry DNS/network | Restore node egress/resolution | Node pull succeeds |
| TLS certificate failure | Repair registry/runtime trust chain | Validated TLS pull |
| Missing ConfigMap/Secret key | Restore approved key/reference | Container starts |
| Invalid command | Correct image/command/args | Process stays healthy |
| Incompatible architecture | Publish correct platform image | Runtime starts |
| Slow startup | Fix startup path; tune probe based on evidence | Stable readiness |
| Volume mount failure | Repair CSI/PV topology/permissions | Mount and application health |

**Rollback gate:** if a rollout caused the incident, confirm previous revision compatibility with database schema, API contracts and persisted state before rollback. Do not use blind rollbacks for irreversible migrations.

## 12. Lab 9 — Image registry and runtime incident tabletop

**Scenario:** an application rollout at 14:00 UTC changes its image to a private registry. At 14:02, new Pods show \`ImagePullBackOff\`. Existing replicas continue serving but capacity is below the PDB target. Events show \`unauthorized\`; a registry credential was rotated that morning.

### Required incident actions

1. Confirm customer impact, rollout revision and desired/available replicas.
2. Verify the exact image digest and whether the tag exists.
3. Confirm the failing Pod's ServiceAccount and imagePullSecrets references.
4. Validate registry authorization without exposing credentials.
5. Check whether a node-specific egress or identity issue also exists.
6. Preserve healthy existing Pods and avoid disruptive maintenance.
7. Choose credential repair or approved rollback with a documented approver.
8. Verify image pull success, readiness, Service endpoints and request SLIs.
9. Document detection delay, contributing factors and prevention controls.

**Expected:** an evidence-backed response that does not weaken registry security or delete healthy replicas unnecessarily.

## 13. Node and runtime troubleshooting escalation

When Kubernetes Events indicate a runtime or node-level failure, escalate using approved node diagnostics:

- Kubelet logs and status.
- Container runtime health (containerd/CRI).
- Image filesystem capacity and inode pressure.
- Registry DNS, proxy, routing, firewall and certificate trust.
- CNI Pod sandbox creation failures.
- CSI volume mount and attach failures.
- Node architecture and runtime compatibility.

For managed EKS/AKS, use approved cloud diagnostics and access mechanisms; do not assume SSH or privileged debug Pods are permitted. Avoid changing container runtime settings on production nodes without a tested change plan.

## 14. Production runbook — Container will not start

### Detect and scope

1. Record cluster, namespace, deployment, Pod, node and incident window.
2. Confirm customer SLIs and available replicas.
3. Determine whether all nodes or only one node/zone are affected.

### Diagnose

1. Inspect \`kubectl describe pod\`, Events and container waiting reason.
2. Separate image pull from config, runtime, process and probe failures.
3. Check image reference/digest, registry identity and network path.
4. Inspect ConfigMap/Secret references and startup command safely.
5. Correlate rollout, node and registry changes with failure timing.

### Mitigate

1. Preserve existing healthy capacity and PDB protections.
2. Apply only approved image, credential, config or infrastructure changes.
3. Roll back only when compatibility and data safety are confirmed.
4. Verify new Pod starts, becomes Ready and receives traffic.

### Close

Record exact error message, cause, mitigation, detection gap, customer impact and preventive action owner.

## 15. Prevention and operational controls

- Pin production images to immutable digests or enforce immutable tags.
- Validate image existence, platform compatibility and signatures in CI.
- Test registry authentication, pull permissions and network paths before rollout.
- Use scoped image pull credentials with rotation monitoring.
- Validate ConfigMap/Secret references and required keys at deployment time.
- Check container command, entrypoint and startup behavior in staging.
- Configure probes around measured startup and dependency characteristics.
- Alert on sustained unavailable replicas and image pull failure trends.
- Maintain registry redundancy/caching strategy appropriate to the platform.
- Document recovery and rollback ownership.

## 16. Evidence template

\`\`\`text
Incident:
Cluster/context:
Namespace/workload:
Time window (UTC):
Affected Pod UID / node / zone:
Image tag and digest:
ImagePullPolicy:
ServiceAccount / pull Secret references (names only):
Waiting reason / Event message:
Last exit code / previous logs:
Rollout revision / recent change:
Registry response / network checks:
Customer SLIs and available replicas:
Confirmed cause:
Mitigation and approver:
Rollback plan:
Recovery verification:
Follow-up actions:
\`\`\`

## 17. Acceptance checklist

- [ ] Container startup stages and failure reasons distinguished.
- [ ] Read-only Pod, Event and log evidence captured.
- [ ] Image tag, digest and pull policy inspected.
- [ ] Registry auth, TLS, DNS and architecture failure paths reviewed.
- [ ] imagePullSecrets and ServiceAccount relationships validated safely.
- [ ] Missing image staging exercise completed or marked not run.
- [ ] Missing ConfigMap key exercise completed or marked not run.
- [ ] Invalid startup command exercise completed or marked not run.
- [ ] Probe behavior distinguished from process exit and runtime errors.
- [ ] Rollout recovery and rollback gates documented.
- [ ] Incident tabletop and runbook acceptance completed.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

## 18. Cleanup

Only remove the isolated training namespace:

\`\`\`powershell
kubectl -n ch062 get pods,configmaps
kubectl delete namespace ch062
\`\`\`

Delete local lab YAML files only if no longer needed. This chapter does not mutate production Deployments, registries or nodes.

**Status:** Draft — runtime validation and technical review pending.

## 19. References

- [Kubernetes Images](https://kubernetes.io/docs/concepts/containers/images/)
- [Pull an Image from a Private Registry](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/)
- [Debug Running Pods](https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/)
- [Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Configure Liveness, Readiness and Startup Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/)
- [Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Kubernetes Troubleshooting](https://kubernetes.io/docs/tasks/debug/)

**Next:** Chapter 063 — Pending, Evicted, OOMKilled and CrashLoopBackOff Pods.
