# Chapter 037 — Secret Management and Rotation

**Track:** Kubernetes Administration · **Part 08 — Configuration Management**  
**Status:** Draft — runtime validation and technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, platform engineers  
**Prerequisites:** Chapter 036; kubectl, Windows PowerShell, isolated Kubernetes lab cluster

## 1. Production scenario

A database password is due for rotation. A Kubernetes Deployment injects the password through an environment variable, while the database still accepts only the old credential. Updating the Kubernetes Secret alone causes new Pods to fail authentication; restarting all Pods simultaneously can cause an outage. The incident team needs a controlled migration with validation, revocation and rollback.

A second incident involves a potentially exposed credential in a CI log. Operators must rotate the upstream credential, assess affected consumers, revoke the exposed value and avoid spreading it further through troubleshooting output.

### Learning objectives

1. Explain the credential lifecycle from creation to revocation.
2. Distinguish Kubernetes Secret objects from upstream credential authorities.
3. Compare environment injection, projected volumes and external secret delivery.
4. Demonstrate a staged rotation with overlapping credentials.
5. Detect stale Pods and validate new authentication without printing credentials.
6. Assess RBAC, encryption at rest, auditability and workload identity.
7. Complete seven labs, including an incident simulation and acceptance report.

## 2. Secret management architecture

```text
Secret authority (database / cloud IAM / vault)
                |
       create / rotate / revoke
                |
     secret delivery controller
                |
         Kubernetes Secret
                |
       +--------+---------+
       |                  |
  Pod env at start   projected volume
       |                  |
 rollout required    eventual refresh + app reload
       |                  |
       +------ application+
                |
      upstream authentication
```

**Critical distinction:** Kubernetes Secret updates change only the object in the Kubernetes API. They do not change the password, key or token recognized by an upstream database or API. Coordinate both sides and verify the application before revoking the previous credential.

## 3. Rotation strategies

| Strategy | Pattern | Operational consideration |
|---|---|---|
| Dual credentials | Create new identity, switch consumers, revoke old | Best for zero/low downtime where supported |
| Overlapping key versions | Both old and new accepted temporarily | Limit overlap and audit usage |
| In-place password change | Same account password replaced | Can break existing or newly started clients |
| Short-lived identity | Workload identity or renewable token | Preferred when supported; requires refresh logic |
| Certificate rotation | New cert/key, trust overlap, revoke old | Account for CA trust, expiry and reload |
| Emergency rotation | Contain exposure, rotate and revoke rapidly | Coordinate incident response and evidence |

Never assume a rollout restart alone provides safe rotation. Database client pools, long-lived connections, sidecars and multiple applications may retain old credentials.

## 4. Lab setup

Use an isolated cluster and **fake credentials only**. The labs simulate an upstream credential authority with a ConfigMap; this is intentionally not a real secret manager and must not be used as a production pattern. All values are demonstration strings.

```powershell
kubectl config current-context
kubectl get nodes
kubectl create namespace ch037
```

The lab uses a fake application that checks whether its injected credential matches an accepted version string. No actual database, cloud API or production secret is involved.

## 5. Lab 1 — Create initial Secret and simulated authority

Save `ch037-baseline.yaml`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-credential
  namespace: ch037
type: Opaque
stringData:
  token: "demo-version-a"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: accepted-versions
  namespace: ch037
data:
  versions: |
    demo-version-a
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: credential-client
  namespace: ch037
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: credential-client
  template:
    metadata:
      labels:
        app: credential-client
    spec:
      containers:
        - name: client
          image: busybox:1.36
          command:
            - sh
            - -c
            - |
              while true; do
                if grep -Fxq "$APP_TOKEN" /authority/versions; then
                  echo "authentication-ok"
                else
                  echo "authentication-failed"
                fi
                sleep 10
              done
          env:
            - name: APP_TOKEN
              valueFrom:
                secretKeyRef:
                  name: app-credential
                  key: token
          volumeMounts:
            - name: authority
              mountPath: /authority
              readOnly: true
          readinessProbe:
            exec:
              command: ["sh", "-c", "grep -Fxq \"$APP_TOKEN\" /authority/versions"]
            periodSeconds: 5
        volumes:
          - name: authority
            configMap:
              name: accepted-versions
```

```powershell
kubectl apply -f .\ch037-baseline.yaml
kubectl -n ch037 rollout status deployment/credential-client --timeout=180s
kubectl -n ch037 get deployment,pods
kubectl -n ch037 logs deployment/credential-client --tail=10
```

**Expected:** two ready replicas, with `authentication-ok` messages. The simulated authority uses a ConfigMap only to illustrate accepted credential versions; production authentication must use the real upstream service.

## 6. Lab 2 — Demonstrate the danger of changing only Kubernetes Secret

**Do not perform this sequence in production.** In the disposable lab, change the Secret's dummy token while the simulated authority accepts only the old value:

```powershell
kubectl -n ch037 patch secret app-credential --type=merge -p '{"stringData":{"token":"demo-version-b"}}'
kubectl -n ch037 get secret app-credential -o jsonpath='{.metadata.resourceVersion}'
kubectl -n ch037 get pods -l app=credential-client
```

Existing Pods remain ready because their environment variables were captured at startup. A new Pod created now would receive version B and fail readiness because the authority still accepts only A. **Do not print the environment variable or Secret value.**

Restore the initial lab Secret before continuing:

```powershell
kubectl apply -f .\ch037-baseline.yaml
```

**Expected:** existing Pods remain on their startup value; a Secret update does not itself restart the Deployment.

## 7. Lab 3 — Prepare a dual-credential overlap window

Modify the simulated authority to accept both versions:

```powershell
kubectl -n ch037 patch configmap accepted-versions --type=merge -p '{"data":{"versions":"demo-version-a\ndemo-version-b\n"}}'
kubectl -n ch037 get configmap accepted-versions -o jsonpath='{.metadata.resourceVersion}'
```

The mounted ConfigMap is refreshed eventually by kubelet. Verify that the original two replicas remain Ready before proceeding:

```powershell
kubectl -n ch037 get deployment credential-client
kubectl -n ch037 get pods -l app=credential-client
```

**Expected:** old credential remains accepted during the overlap. In a real database, this step means creating a second credential/account or otherwise enabling overlap on the upstream authority, not editing a ConfigMap.

## 8. Lab 4 — Roll out the new credential safely

Patch the lab Secret to version B, then trigger a controlled Deployment restart:

```powershell
kubectl -n ch037 patch secret app-credential --type=merge -p '{"stringData":{"token":"demo-version-b"}}'
kubectl -n ch037 rollout restart deployment/credential-client
kubectl -n ch037 rollout status deployment/credential-client --timeout=180s
kubectl -n ch037 get deployment,pods -o wide
kubectl -n ch037 logs deployment/credential-client --tail=15
```

**Expected:** two ready replicas and `authentication-ok` messages, with no credential values logged. If readiness fails, stop before revoking A; inspect Pod events, upstream accepted versions and projection refresh. A Kubernetes rollout with `maxUnavailable: 0` does not by itself guarantee zero downtime when nodes lack capacity, readiness is inaccurate, or upstream authentication is unavailable.

## 9. Lab 5 — Revoke the old credential after validation

After all clients are Ready on version B, change the simulated authority to accept only B:

```powershell
kubectl -n ch037 patch configmap accepted-versions --type=merge -p '{"data":{"versions":"demo-version-b\n"}}'
kubectl -n ch037 get deployment credential-client
kubectl -n ch037 get pods -l app=credential-client
```

Wait for projected ConfigMap updates and confirm application readiness. In a real rotation, verify **all** known consumers, batch jobs, CronJobs, rollback versions and external clients have migrated before revoking the previous credential.

**Expected:** service stays Ready after old-version revocation. Record the time when the old credential is no longer accepted.

## 10. Lab 6 — Stale-credential and failed-rotation investigation

Investigate without displaying Secret values:

```powershell
kubectl -n ch037 get secret app-credential -o custom-columns=NAME:.metadata.name,RESOURCEVERSION:.metadata.resourceVersion
kubectl -n ch037 get pods -l app=credential-client -o wide
kubectl -n ch037 describe deployment credential-client
kubectl -n ch037 rollout history deployment/credential-client
kubectl -n ch037 get events --sort-by=.lastTimestamp
kubectl -n ch037 logs deployment/credential-client --tail=30
```

Failure patterns:
- New Pod fails readiness: upstream still accepts only old credential, bad key reference, or wrong namespace.
- Old Pod continues working: environment value is stale, but upstream still permits it.
- Old Pod stops working after revocation: not all clients were rolled out.
- Mounted Secret changes but app remains stale: application does not reread or reload the file.
- External secret controller fails: provider authentication, refresh policy, rate limit, or sync errors.

**Rollback:** during overlap, restore the last working Kubernetes Secret and restart the Deployment if necessary. After old credentials are revoked upstream, rolling back the Kubernetes manifest alone may fail; restore upstream authorization through an approved procedure or rotate forward to a new credential. Never assume `kubectl rollout undo` restores previous Secret contents.

## 11. Lab 7 — Emergency exposure and rotation acceptance

Simulated incident: a dummy token appears in CI logs. No real token is exposed in this exercise.

Respond in order:
1. Identify affected authority, applications, environments, service accounts and exposure window.
2. Restrict log/artifact access and preserve forensic evidence without reproducing the token.
3. Generate a replacement credential using the approved authority.
4. Deliver replacement through the approved Kubernetes integration.
5. Roll consumers safely; verify readiness and real authentication.
6. Revoke the exposed credential promptly, accounting for incident severity and service continuity.
7. Audit subsequent use of the compromised credential and review blast radius.
8. Rotate any derived credentials if the exposed token could access them.
9. Document timeline, detection, RTO, owner and preventive action.

### Acceptance evidence

| Check | Required evidence |
|---|---|
| Initial deployment | Two ready replicas |
| Secret-only change | Existing env values not refreshed |
| Dual credential overlap | Both versions accepted before rollout |
| New credential rollout | Ready replicas and successful simulated auth |
| Revocation | Old version removed after validation |
| Incident investigation | No credential values printed |
| Rollback | Explicit upstream and Kubernetes steps |
| Security review | RBAC, encryption, audit and secret-delivery risks |

## 12. External secret managers and workload identity

Production environments commonly use cloud secret managers, Vault or Kubernetes secret-sync integrations. These have different trust models:

- **External Secrets Operator (ESO):** reconciles external provider values into Kubernetes Secret objects. Access to the resulting Kubernetes Secret remains a security concern.
- **Secrets Store CSI Driver:** can mount provider-backed secret material into Pods; optional syncing to Kubernetes Secret is configuration-dependent. Application reload behavior remains relevant.
- **Workload identity:** maps Kubernetes workloads to short-lived cloud identity without embedding static cloud API keys. Examples include supported EKS/AKS provider integrations.
- **Vault dynamic credentials:** may issue short-lived database credentials with lease and revocation semantics. Applications must handle renewal and connection rotation.

Do not assume any of these components is installed. Verify the controller/driver version, provider permissions, service account identity, refresh interval, failure behavior, audit trails and availability dependencies before adopting them.

## 13. Security controls and audit

```powershell
kubectl auth can-i get secrets -n ch037
kubectl auth can-i list secrets -n ch037
kubectl auth can-i create pods -n ch037
kubectl -n ch037 get serviceaccounts,rolebindings
kubectl -n ch037 get pods -o custom-columns=NAME:.metadata.name,SA:.spec.serviceAccountName
```

Operational controls:
- Least-privilege RBAC and separate identities for applications.
- Encryption at rest for Kubernetes API datastore, with key management and rotation.
- Short-lived credentials and workload identity where supported.
- Restrict Secret values in Git, CI logs, debugging sessions and incident artifacts.
- Audit Secret access and external credential use without logging credential contents.
- Explicit ownership, rotation frequency, expiry monitoring and emergency revocation procedure.
- Avoid exposing secrets through `kubectl exec ... printenv`, process arguments or verbose application logs.
- Recognize that Pod creation permission may allow indirect access to Secrets in the namespace.

## 14. Production rotation runbook

**Pre-change:** identify credential authority, all consumers, current expiry, rotation type, overlap support, backup access path, rollout strategy and abort criteria.

**Execution:** provision replacement upstream → validate replacement out of band → update delivery system → roll consumers gradually → verify readiness, authentication and application SLIs → revoke old credential → monitor failures.

**Recovery:** if new credentials fail, keep or restore overlap when possible; correct upstream permissions or Secret delivery; roll back only when old credentials remain accepted. For compromised credentials, prioritize containment and rotate forward rather than extending exposure indefinitely.

**Post-change:** verify no active use of old credential, record credential version identifiers (not values), review audit logs, and close the change after monitoring.

## 15. Troubleshooting matrix

| Symptom | Likely cause | Action |
|---|---|---|
| New Pods fail auth | Upstream not updated, wrong Secret key | Verify authority and Pod references |
| Old Pods fail after revocation | Stale environment values | Identify and restart remaining consumers |
| Mounted Secret stale | Kubelet refresh or subPath | Inspect mount pattern and app reload |
| ESO sync failing | Provider auth/permissions, controller | Inspect sync status and controller logs |
| CSI secret mount fails | Provider driver, identity, node plugin | Inspect Pod events and driver logs |
| Rollback fails | Old credential revoked upstream | Coordinate upstream restoration or forward rotation |
| Credential exposed | Logs, RBAC, Git history | Incident containment, rotation and audit |

## 16. Cleanup

Only in the disposable namespace:

```powershell
kubectl -n ch037 get deployment,pods,configmaps,secrets
kubectl delete namespace ch037
```

The demo Secret contains fake values. Do not copy this simulated authority architecture into production. Do not delete shared secret managers, cloud credentials or secret-sync controllers.

## 17. Acceptance checklist

- [ ] Secret authority versus Kubernetes Secret distinction explained.
- [ ] Initial fake credential consumed successfully.
- [ ] Secret-only update behavior demonstrated.
- [ ] Dual-credential overlap established.
- [ ] Controlled Deployment rollout completed.
- [ ] Old credential revoked only after validation.
- [ ] Stale credentials and rollback risks investigated.
- [ ] External secret and workload identity options compared.
- [ ] Emergency exposure response documented.
- [ ] No real credential values logged or committed.
- [ ] Runtime validation and independent review completed before marking Lab Validated.

**Status:** Draft; runtime validation and technical review pending.

## 18. References

- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Good Practices for Kubernetes Secrets](https://kubernetes.io/docs/concepts/security/secrets-good-practices/)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Secrets Store CSI Driver](https://secrets-store-csi-driver.sigs.k8s.io/)
- [External Secrets Operator](https://external-secrets.io/)

**Next:** Chapter 038 — Helm Installation, Charts and Releases.
