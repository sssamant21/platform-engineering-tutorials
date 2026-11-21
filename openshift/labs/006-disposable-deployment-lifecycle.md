# Lab 006 — Disposable Deployment Lifecycle

**Safety:** Non-production only. Use a preapproved disposable project and approved image. No cluster-wide writes. Estimated 25–30 minutes. This lab is a template, **not an executed test**.

## Prerequisites

- `oc` installed and authenticated; verify `oc whoami --show-server` and `oc config current-context`.
- Platform team provides a non-production project, permission to create/delete Deployments and Services, a trusted **immutable image digest** that runs under OpenShift restricted SCC, and the image's actual container port and health endpoint.
- Confirm the namespace is disposable, no shared workloads will be affected, and cleanup is authorized.
- Set `LAB_NS` to your actual namespace. Bash: `export LAB_NS=my-disposable-project`. PowerShell: `$env:LAB_NS="my-disposable-project"`. Commands using `$LAB_NS` below are Bash examples; PowerShell must use `$env:LAB_NS`.

## Preflight (read-only)

```bash
oc whoami
oc whoami --show-server
oc config current-context
oc get namespace "$LAB_NS"
oc auth can-i create deployments.apps -n "$LAB_NS"
oc auth can-i delete deployments.apps -n "$LAB_NS"
oc auth can-i create services -n "$LAB_NS"
oc get deployments -n "$LAB_NS"
```

If any check fails, **stop** and request authorization rather than broadening permissions.

## Manifest preparation (offline)

Create `ocp-lab-006.yaml` locally, replacing the placeholders with approved values. The placeholders are intentionally invalid until replaced.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ocp-lab-006
  labels:
    app.kubernetes.io/name: ocp-lab-006
    training.openai.example/scope: disposable
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: ocp-lab-006
  template:
    metadata:
      labels:
        app.kubernetes.io/name: ocp-lab-006
    spec:
      containers:
        - name: web
          image: REGISTRY/APP@sha256:REPLACE_WITH_APPROVED_DIGEST
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 250m
              memory: 256Mi
          readinessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: ocp-lab-006
  labels:
    app.kubernetes.io/name: ocp-lab-006
spec:
  selector:
    app.kubernetes.io/name: ocp-lab-006
  ports:
    - port: 8080
      targetPort: 8080
```

The image, port and health endpoint are illustrative and must match the approved application. Do not use a real production image without authorization. The application must support OpenShift arbitrary-UID execution. The label is a convenience, **not a security boundary**.

## Execute (approved disposable project only)

```bash
oc -n "$LAB_NS" apply --dry-run=server -f ocp-lab-006.yaml
oc -n "$LAB_NS" apply -f ocp-lab-006.yaml
oc -n "$LAB_NS" rollout status deployment/ocp-lab-006 --timeout=120s
oc -n "$LAB_NS" get deployment,replicaset,pod,service -l app.kubernetes.io/name=ocp-lab-006 -o wide
oc -n "$LAB_NS" describe deployment ocp-lab-006
oc -n "$LAB_NS" get events --sort-by=.lastTimestamp
```

**Expected:** admission succeeds, Deployment available replica count is 1, Pod becomes Ready, and the Service selects the pod. These are expected outcomes, not observed results. Server-side dry run still sends a request to the API and may trigger admission checks; use only in the approved test environment.

## Failure investigation (no induced outage)

If `rollout status` times out, check events, `oc describe deployment ocp-lab-006`, and `oc describe pod <lab-pod>`. If the pod fails SCC admission, do not grant privileged SCC; choose a compatible image. If the readiness probe fails, verify its path/port against the actual application. Record failure evidence; do not mark the lab passed.

## Cleanup (state-changing; only after owner approval)

```bash
# Inspect the exact objects before deletion; do not use broad selectors.
oc -n "$LAB_NS" get deployment ocp-lab-006
oc -n "$LAB_NS" get service ocp-lab-006
oc -n "$LAB_NS" delete -f ocp-lab-006.yaml
oc -n "$LAB_NS" get deployment ocp-lab-006
oc -n "$LAB_NS" get service ocp-lab-006
```

The final two lookups should return NotFound. If the objects existed before this exercise or are shared, **do not delete them**. If the lab fails before creation, cleanup may report NotFound; document it.

## Evidence record

| Field | Result |
| --- | --- |
| UTC timestamp | Not executed |
| Sanitized cluster / OCP version | Not executed |
| Namespace and permissions | Not executed |
| Approved image digest / probe verified | Not executed |
| Server-side admission | Not executed |
| Replica and readiness state | Not executed |
| Failure observations | Not executed |
| Cleanup confirmation | Not executed |
| Independent reviewer | Pending |

**Status:** Drafted; no runtime test or production approval.
