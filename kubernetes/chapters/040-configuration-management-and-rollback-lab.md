# Chapter 040 — Configuration Management and Rollback Lab

**Track:** Kubernetes Administration · **Part 08 — Configuration Management (final capstone)**  
**Status:** Draft — execution and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators and platform engineers  
**Prerequisites:** Chapters 036–039; Windows PowerShell, kubectl, Helm 3/4; disposable Kubernetes cluster

## 1. Production incident scenario

A platform team manages a web application across staging and production-like environments. A configuration change breaks the application's readiness check. A subsequent Helm upgrade points to a nonexistent container image. Meanwhile, a credential rotation leaves a consumer using an old environment-injected token. Operators must recover without exposing credentials, deleting unrelated resources or assuming that a Deployment rollback restores external state.

**Capstone goal:** integrate ConfigMaps, Secrets, credential rotation, Helm release history, Kustomize overlays, controlled rollback and incident evidence into a repeatable recovery exercise.

### Objectives

1. Establish a healthy, versioned baseline with a measurable readiness SLI.
2. Deploy environment-specific configuration with Kustomize.
3. Reproduce a missing-key application configuration failure.
4. Diagnose a failed Helm release and restore a known-good revision.
5. Demonstrate safe overlap and revocation during a simulated credential rotation.
6. Explain configuration drift, rollback limits, and secret-exposure controls.
7. Produce an incident report, recovery checklist and acceptance evidence.

## 2. Architecture and fault boundaries

```text
Git source ──> Kustomize overlay ──> ConfigMap ──┐
                                                 ├─> Pod environment / files
Secret authority ──> Kubernetes Secret ──────────┘
                                                 |
Helm chart + values ──> release ──> Deployment ──> application
                             |                       |
                      revision history          readiness SLI
```

**Rollback boundaries:** a Helm rollback restores release-managed Kubernetes manifests, not arbitrary externally managed ConfigMaps, Secrets, upstream passwords, database migrations, or persistent data. A Kustomize source revert must be rendered and reapplied; it has no built-in Helm-style release history. Environment variables are fixed at container startup. Projected Secret/ConfigMap files refresh eventually unless mounted through `subPath`; the application must reread them.

## 3. Safety, prerequisites and lab layout

Use only a disposable cluster. Never store actual passwords in manifests or Git, and never print Secret values in incident logs.

```powershell
kubectl config current-context
kubectl get nodes
helm version
kubectl create namespace ch040
New-Item -ItemType Directory -Force .\ch040\config\base
New-Item -ItemType Directory -Force .\ch040\config\overlays\lab
New-Item -ItemType Directory -Force .\ch040\chart\templates
```

The labs use a **fake** credential version to simulate an upstream authority. This is a training model, not an acceptable production credential store.

### File layout

```text
ch040/
  config/
    base/
      kustomization.yaml
      configmap.yaml
    overlays/lab/
      kustomization.yaml
      patch.yaml
  chart/
    Chart.yaml
    values.yaml
    templates/
      deployment.yaml
      service.yaml
  credential.yaml
  authority.yaml
```

## 4. Lab 1 — Build and verify environment configuration

Save `ch040/config/base/configmap.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ch040-settings
data:
  APP_MODE: "base"
  REQUIRED_SETTING: "healthy"
```

Save `ch040/config/base/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - configmap.yaml
```

Save `ch040/config/overlays/lab/patch.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ch040-settings
data:
  APP_MODE: "lab"
```

Save `ch040/config/overlays/lab/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: ch040
resources:
  - ../../base
patches:
  - path: patch.yaml
```

```powershell
kubectl kustomize .\ch040\config\overlays\lab
kubectl diff -k .\ch040\config\overlays\lab
kubectl apply -k .\ch040\config\overlays\lab
kubectl -n ch040 get configmap ch040-settings -o jsonpath='{.data.REQUIRED_SETTING}'
```

**Expected:** rendered ConfigMap is in `ch040`, `APP_MODE=lab`, `REQUIRED_SETTING=healthy`. The initial `kubectl diff` can exit nonzero because the resource does not yet exist; review its output rather than treating any nonzero exit code as an application failure.

## 5. Lab 2 — Package and deploy a healthy Helm release

Save `ch040/chart/Chart.yaml`:

```yaml
apiVersion: v2
name: ch040-app
description: Configuration recovery capstone
type: application
version: 0.1.0
appVersion: "1.0"
```

Save `ch040/chart/values.yaml`:

```yaml
replicaCount: 2
image:
  repository: busybox
  tag: "1.36"
```

Save `ch040/chart/templates/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}-app
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ .Release.Name }}-app
  template:
    metadata:
      labels:
        app: {{ .Release.Name }}-app
    spec:
      containers:
        - name: app
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          command:
            - sh
            - -c
            - |
              while true; do
                if [ "$REQUIRED_SETTING" != "healthy" ]; then
                  echo "configuration-invalid"
                fi
                sleep 5
              done
          env:
            - name: REQUIRED_SETTING
              valueFrom:
                configMapKeyRef:
                  name: ch040-settings
                  key: REQUIRED_SETTING
          readinessProbe:
            exec:
              command: ["sh", "-c", "test \"$REQUIRED_SETTING\" = healthy"]
            periodSeconds: 5
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
            limits:
              cpu: 100m
              memory: 64Mi
```

Save `ch040/chart/templates/service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ .Release.Name }}-app
spec:
  selector:
    app: {{ .Release.Name }}-app
  ports:
    - port: 80
      targetPort: 80
  type: ClusterIP
```

This Service is intentionally only a release-resource example; the BusyBox application does not listen on TCP 80. **Do not use Service connectivity as the SLI for this lab**; use Pod readiness.

```powershell
helm lint .\ch040\chart
helm template capstone .\ch040\chart -n ch040
helm install capstone .\ch040\chart -n ch040 --wait --timeout 3m
kubectl -n ch040 rollout status deployment/capstone-app --timeout=180s
kubectl -n ch040 get deploy,pods,svc
helm history capstone -n ch040
```

**Expected:** two Ready replicas and Helm revision 1 deployed. Record baseline timestamps and the observed readiness SLI.

## 6. Lab 3 — Inject missing-key failure and recover safely

Change `REQUIRED_SETTING` to `BROKEN_SETTING` in the **lab overlay's base ConfigMap** and apply the Kustomize overlay:

```powershell
kubectl apply -k .\ch040\config\overlays\lab
kubectl -n ch040 get configmap ch040-settings
```

**Important:** existing Pods still have the old environment snapshot, so the change alone does not break them. Trigger a controlled restart **only in this disposable lab**:

```powershell
kubectl -n ch040 rollout restart deployment/capstone-app
kubectl -n ch040 get pods -w
```

Stop watching with Ctrl+C. New Pods should report a configuration error because `REQUIRED_SETTING` is missing. Inspect:

```powershell
kubectl -n ch040 describe deployment capstone-app
kubectl -n ch040 get pods
kubectl -n ch040 get events --sort-by=.lastTimestamp
```

**Expected:** newly created Pods fail configuration/startup; old healthy Pods may remain because rolling updates normally preserve availability. Do not delete the Secret or reinstall the Helm chart.

Restore the base ConfigMap's original `REQUIRED_SETTING: "healthy"` key and remove `BROKEN_SETTING`, then:

```powershell
kubectl apply -k .\ch040\config\overlays\lab
kubectl -n ch040 rollout status deployment/capstone-app --timeout=180s
kubectl -n ch040 get pods
```

**Expected:** new Pods become Ready after the key is restored. If the Deployment is still stuck, inspect events and restart the Deployment deliberately; do not assume that a Helm rollback would restore this Kustomize-managed ConfigMap.

## 7. Lab 4 — Inject a failed Helm upgrade and recover

With configuration healthy, simulate an unavailable image:

```powershell
helm upgrade capstone .\ch040\chart -n ch040 --set image.tag=ch040-nonexistent --wait --timeout 90s
helm history capstone -n ch040
helm status capstone -n ch040
kubectl -n ch040 get deploy,rs,pods -o wide
kubectl -n ch040 get events --sort-by=.lastTimestamp
```

**Expected:** upgrade fails or times out because the new image cannot be pulled. Record the failed revision and last healthy revision. On a clean lab installation, the first healthy revision is 1, but **always verify history**.

Recover by rolling back to the verified healthy revision:

```powershell
helm rollback capstone 1 -n ch040 --wait --timeout 3m
kubectl -n ch040 rollout status deployment/capstone-app --timeout=180s
helm history capstone -n ch040
kubectl -n ch040 get pods
```

**Expected:** two Ready replicas and a new Helm revision representing the rollback. Rollback does not restore external credential state or arbitrary ConfigMaps.

## 8. Lab 5 — Simulated Secret rotation and stale environment

Save `ch040/credential.yaml`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: demo-credential
  namespace: ch040
type: Opaque
stringData:
  token: demo-v1
```

Save `ch040/authority.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: demo-authority
  namespace: ch040
data:
  accepted: |
    demo-v1
```

These are dummy values, not actual credentials.

```powershell
kubectl apply -f .\ch040\credential.yaml
kubectl apply -f .\ch040\authority.yaml
```

Save `ch040/rotation-pod.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: rotation-client
  namespace: ch040
spec:
  containers:
    - name: client
      image: busybox:1.36
      command: ["sh", "-c", "while true; do if grep -Fxq \"$TOKEN\" /authority/accepted; then echo auth-ok; else echo auth-failed; fi; sleep 5; done"]
      env:
        - name: TOKEN
          valueFrom:
            secretKeyRef:
              name: demo-credential
              key: token
      volumeMounts:
        - name: authority
          mountPath: /authority
          readOnly: true
  volumes:
    - name: authority
      configMap:
        name: demo-authority
```

```powershell
kubectl apply -f .\ch040\rotation-pod.yaml
kubectl -n ch040 wait --for=condition=Ready pod/rotation-client --timeout=120s
kubectl -n ch040 logs rotation-client --tail=5
```

**Expected:** `auth-ok`. Updating the Kubernetes Secret to `demo-v2` does **not** change the environment of this running Pod:

```powershell
kubectl -n ch040 patch secret demo-credential --type=merge -p '{"stringData":{"token":"demo-v2"}}'
kubectl -n ch040 logs rotation-client --tail=5
```

**Expected:** existing Pod continues using `demo-v1`. Do not print the token or dump Secret contents.

## 9. Lab 6 — Safe overlap, rotation, revocation and recovery

First update the fake upstream authority to accept both versions:

```powershell
kubectl -n ch040 patch configmap demo-authority --type=merge -p '{"data":{"accepted":"demo-v1\ndemo-v2\n"}}'
```

Wait until the mounted authority file refreshes, then replace the disposable client Pod so it reads the new Secret at startup:

```powershell
kubectl -n ch040 delete pod rotation-client
kubectl apply -f .\ch040\rotation-pod.yaml
kubectl -n ch040 wait --for=condition=Ready pod/rotation-client --timeout=120s
kubectl -n ch040 logs rotation-client --tail=5
```

**Expected:** `auth-ok` on version 2. Then revoke the old dummy version:

```powershell
kubectl -n ch040 patch configmap demo-authority --type=merge -p '{"data":{"accepted":"demo-v2\n"}}'
kubectl -n ch040 logs rotation-client --tail=5
```

**Expected:** authentication remains successful after the ConfigMap projection refreshes. In production, never represent an actual authentication authority with a ConfigMap. Rotate credentials in the database, Vault, cloud IAM or another real authority, validate all consumers, and revoke the old credential only after the overlap and acceptance criteria are satisfied.

**Rollback boundary:** if old credentials have been revoked upstream, restoring a previous Kubernetes Secret or Helm revision alone will not restore authentication. Coordinate upstream recovery or rotate forward.

## 10. Lab 7 — Integrated incident-response acceptance

**Incident ticket:** after a configuration update, the new Pods fail startup. A subsequent Helm upgrade is marked failed. A database credential was recently rotated. The on-call engineer is asked to “roll everything back.”

Required investigation:

```powershell
kubectl config current-context
kubectl -n ch040 get deployment,pods,configmaps,secrets
kubectl -n ch040 get events --sort-by=.lastTimestamp
kubectl -n ch040 describe deployment capstone-app
helm status capstone -n ch040
helm history capstone -n ch040
kubectl kustomize .\ch040\config\overlays\lab
kubectl diff -k .\ch040\config\overlays\lab
kubectl -n ch040 logs rotation-client --tail=10
```

Never include decoded Secret values in the incident record.

### Recovery decision table

| Finding | Correct recovery | Unsafe shortcut |
|---|---|---|
| Missing ConfigMap key | Restore correct key in source and apply overlay | Delete PVC or Secret |
| Invalid container image | Roll back verified Helm revision or fix image | Uninstall release blindly |
| Stale environment credential | Coordinate upstream overlap and controlled restart | Rotate Kubernetes Secret alone |
| Old upstream credential revoked | Rotate forward or approved authority recovery | Assume Helm rollback restores password |
| Live configuration drift | Reconcile source of truth after reviewing diff | Blind force-apply |
| Exposed real credential | Contain, rotate, revoke and audit | Copy token into incident notes |

### Required incident report

Record:
- Cluster context and affected namespace.
- First observed failure and user-facing impact.
- Helm revisions and overlay source revision.
- ConfigMap key mismatch and affected Pods.
- Credential authority state and which consumers were rotated.
- Recovery action, observed **RTO**, measured application readiness and data-loss assessment.
- Whether a rollback had external side effects.
- Prevention: CI render/diff checks, secret rotation runbook, policy controls and ownership.

**RTO** is measured from impact detection to validated recovery. **RPO** applies to persistent application data; this stateless demo does not exercise database restore, so do not invent a storage RPO.

## 11. Production troubleshooting runbook

1. **Establish scope:** namespace, application, release, overlay, user impact and SLI.
2. **Freeze competing changes:** coordinate Helm, GitOps and manual updates to avoid reconciliation races.
3. **Preserve evidence:** collect resource metadata, events, rollout history and logs with secret redaction.
4. **Classify fault:** rendering, admission, missing key, stale environment, failed image, external credential or drift.
5. **Identify ownership:** which resources are Helm-managed, Kustomize-managed or externally managed?
6. **Assess rollback limits:** CRDs, hooks, data migrations, Secrets, external identities and PVCs.
7. **Execute narrow recovery:** fix source configuration or restore known-good Helm revision; coordinate upstream auth separately.
8. **Validate:** Ready replicas, application transactions, error rate, latency and credential acceptance.
9. **Close:** document timeline, RTO, root cause, corrective actions, prevention and owners.

### Preventive controls

- Render and validate Helm charts and all Kustomize overlays in CI.
- Enforce image provenance, resource limits, required keys and policy-as-code checks.
- Use reviewed Git revisions and clear resource ownership.
- Protect Kubernetes Secrets with least-privilege RBAC and encryption at rest.
- Avoid plaintext credentials in Helm values, Git history and logs.
- Prefer workload identity or short-lived credentials where supported.
- Design dual-credential overlap and expiry alerts before production rotations.
- Include application-level health checks; a Ready Pod does not always imply successful database authentication.
- Test rollback in staging and explicitly document irreversible external changes.

## 12. Cleanup

**Only after confirming the namespace and all resources are disposable:**

```powershell
helm list -n ch040
kubectl -n ch040 get all,configmaps,secrets
helm uninstall capstone -n ch040 --wait
kubectl delete namespace ch040
```

Do not remove shared secret managers, StorageClasses, PVCs, cloud credentials or other namespaces. The lab creates no persistent volumes.

## 13. Part 08 capstone acceptance checklist

- [ ] Chapter 036: ConfigMaps and Secrets created and consumed.
- [ ] Chapter 037: stale environment and staged credential rotation demonstrated.
- [ ] Chapter 038: Helm chart installed, failed upgrade diagnosed and rollback verified.
- [ ] Chapter 039: Kustomize base/overlay rendered and applied.
- [ ] Healthy baseline and readiness SLI recorded.
- [ ] Missing-key failure reproduced and recovered.
- [ ] Helm failure reproduced and known-good revision restored.
- [ ] External credential authority versus Kubernetes Secret distinguished.
- [ ] Rotation overlap and revocation validated without logging credentials.
- [ ] Incident report contains actual evidence, RTO and prevention.
- [ ] Lab resources cleaned up safely.
- [ ] Hands-on execution and independent technical review completed before marking Part 08 Lab Validated.

**Part 08 writing milestone:** Chapters 036–040 drafted. Runtime validation and technical review remain pending.

## 14. References

- [Kubernetes ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Kubernetes Kustomize](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/)
- [Helm Documentation](https://helm.sh/docs/)
- [Helm Rollback](https://helm.sh/docs/helm/helm_rollback/)
- [Kubernetes Deployment Rollouts](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)

**Next:** Chapter 041 — Kubernetes Authentication and RBAC (Part 09).
