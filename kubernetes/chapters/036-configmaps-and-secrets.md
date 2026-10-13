# Chapter 036 — ConfigMaps and Secrets

**Track:** Kubernetes Administration · **Part 08 — Configuration Management**  
**Status:** Draft — runtime validation and technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, platform engineers  
**Prerequisites:** Chapters 001–035; kubectl, Windows PowerShell, disposable Kubernetes cluster

## 1. Production scenario

A deployment works in staging but crashes in production because a required configuration key is missing. A separate service continues using an old database password after a Secret is rotated. A well-intentioned troubleshooting command exposes a Secret in terminal history and incident notes.

The operator must distinguish non-sensitive configuration from credentials, understand how configuration reaches containers, validate updates, and restore service without leaking secrets or broadening access.

### Learning objectives

1. Create and inspect ConfigMaps and Secrets without exposing production credentials.
2. Consume values through environment variables, `envFrom`, individual volume mounts and projected volumes.
3. Explain immutable environment snapshots versus eventually refreshed projected files.
4. Reproduce and diagnose missing-key and stale-configuration failures.
5. Understand Secret encoding, encryption at rest, RBAC and workload identity.
6. Demonstrate a controlled Secret update and application restart.
7. Complete seven labs, a production troubleshooting runbook and acceptance evidence.

## 2. Configuration architecture

```text
Git / deployment pipeline
        |
        +-- ConfigMap (non-secret) --+
        |                           |
        +-- Secret (sensitive) ------+--> Pod spec
                                        |
                              +---------+-----------+
                              |                     |
                         env / envFrom        projected volume
                              |                     |
                       process startup       kubelet refresh
                              |                     |
                       restart to update     application reload
```

ConfigMaps and Secrets are namespaced Kubernetes API resources. Both can be consumed as environment variables or mounted files. **Environment values are captured when a container starts**; editing the underlying object does not update already-running environment variables. Mounted ConfigMap and Secret files are updated eventually by kubelet when the volume is not mounted via `subPath`; applications must reread or reload them. A `subPath` mount does not receive automatic updates.

**Security distinction:** ConfigMaps are not appropriate for passwords or tokens. Secret `data` values are base64-encoded, **not encrypted by base64**. Encryption at rest must be configured and verified at the Kubernetes API datastore layer. Secrets can still be exposed through overly broad RBAC, compromised Pods, logs, debugging tools or backup exports.

## 3. ConfigMap and Secret fundamentals

| Topic | ConfigMap | Secret |
|---|---|---|
| Intended use | Non-sensitive settings | Credentials, certificates, keys |
| Namespace scoped | Yes | Yes |
| Environment variables | Yes | Yes |
| Volume projection | Yes | Yes |
| `data` format | UTF-8 strings | Base64-encoded values |
| `binaryData` / `stringData` | `binaryData` supported | `stringData` write convenience |
| Typical update | App reload or rollout | Controlled rotation and rollout |
| Default API confidentiality | No secrecy guarantee | RBAC and encryption configuration required |

A Secret can use `stringData` in a manifest for authoring, but it is still **plaintext in the manifest and Git history**. Do not commit actual credentials, including values in examples copied into production. Kubernetes Secret size is limited (typically 1 MiB per object); large configuration belongs elsewhere.

## 4. Lab setup and safety

Use a disposable context. All credential values below are explicitly fake and must never be reused for real systems.

```powershell
kubectl config current-context
kubectl get nodes
kubectl create namespace ch036
kubectl -n ch036 get configmaps,secrets
```

Avoid `kubectl get secret -o yaml` and `kubectl describe secret` in shared incident transcripts unless access is justified; the former exposes encoded data that is trivial to decode. Avoid putting real secrets into PowerShell command history.

## 5. Lab 1 — Create and validate a ConfigMap

Save `ch036-configmap.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-settings
  namespace: ch036
data:
  APP_MODE: "staging"
  LOG_LEVEL: "info"
  feature-flags.yaml: |
    featureA: true
    featureB: false
```

```powershell
kubectl apply -f .\ch036-configmap.yaml
kubectl -n ch036 get configmap app-settings
kubectl -n ch036 describe configmap app-settings
kubectl -n ch036 get configmap app-settings -o jsonpath='{.data.LOG_LEVEL}'
```

**Expected:** `APP_MODE`, `LOG_LEVEL` and `feature-flags.yaml` exist. No credentials are stored in the ConfigMap. A ConfigMap's keys are case-sensitive.

## 6. Lab 2 — Create a Secret using dummy credentials

Save `ch036-secret.yaml`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: demo-credentials
  namespace: ch036
type: Opaque
stringData:
  username: "demo-user"
  password: "not-a-real-password"
```

```powershell
kubectl apply -f .\ch036-secret.yaml
kubectl -n ch036 get secret demo-credentials
kubectl -n ch036 describe secret demo-credentials
```

**Expected:** Secret exists and lists keys and byte counts without printing their values. The example's plaintext exists on disk in the lab YAML. In production, use an approved secret manager and delivery integration; do not store actual `stringData` values in source control.

**Important:** Secret type `Opaque` is generic. Other types such as `kubernetes.io/tls`, `kubernetes.io/dockerconfigjson` and service-account-token Secrets have specific conventions. Prefer projected, short-lived service account tokens over manually created long-lived tokens.

## 7. Lab 3 — Consume configuration and credentials as environment variables

Save `ch036-env-pod.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: env-consumer
  namespace: ch036
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "echo \"mode=$APP_MODE level=$LOG_LEVEL user=$DB_USER\"; sleep 36000"]
      env:
        - name: APP_MODE
          valueFrom:
            configMapKeyRef:
              name: app-settings
              key: APP_MODE
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: app-settings
              key: LOG_LEVEL
        - name: DB_USER
          valueFrom:
            secretKeyRef:
              name: demo-credentials
              key: username
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: demo-credentials
              key: password
```

```powershell
kubectl apply -f .\ch036-env-pod.yaml
kubectl -n ch036 wait --for=condition=Ready pod/env-consumer --timeout=120s
kubectl -n ch036 logs env-consumer
```

**Expected:** log shows `mode=staging level=info user=demo-user` but **never prints the password**. Application processes can still expose environment secrets through diagnostics, process inspection or crash reports; environment injection is not inherently more secure than mounted files.

`envFrom` can import all valid environment-variable keys from a ConfigMap or Secret. It is convenient but makes configuration dependencies less explicit; invalid environment-variable names are skipped with events.

## 8. Lab 4 — Project ConfigMap and Secret as files

Save `ch036-volume-pod.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: volume-consumer
  namespace: ch036
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "sleep 36000"]
      volumeMounts:
        - name: config
          mountPath: /etc/app-config
          readOnly: true
        - name: credentials
          mountPath: /etc/app-secret
          readOnly: true
  volumes:
    - name: config
      configMap:
        name: app-settings
    - name: credentials
      secret:
        secretName: demo-credentials
        defaultMode: 0400
```

```powershell
kubectl apply -f .\ch036-volume-pod.yaml
kubectl -n ch036 wait --for=condition=Ready pod/volume-consumer --timeout=120s
kubectl -n ch036 exec volume-consumer -- ls -l /etc/app-config
kubectl -n ch036 exec volume-consumer -- cat /etc/app-config/LOG_LEVEL
kubectl -n ch036 exec volume-consumer -- ls -l /etc/app-secret
```

**Expected:** configuration and Secret files are present. Do not print real Secret file contents into logs. `defaultMode: 0400` is an octal YAML literal; effective access also depends on UID/GID, filesystem and Pod security context. Read-only mounts prevent normal writes through that mount but do not prevent a privileged or compromised process from reading accessible credentials.

## 9. Lab 5 — Observe configuration updates: environment versus volume

Update only the non-sensitive ConfigMap:

```powershell
kubectl -n ch036 patch configmap app-settings --type=merge -p '{"data":{"LOG_LEVEL":"debug"}}'
kubectl -n ch036 get configmap app-settings -o jsonpath='{.data.LOG_LEVEL}'
kubectl -n ch036 exec env-consumer -- printenv LOG_LEVEL
kubectl -n ch036 exec volume-consumer -- cat /etc/app-config/LOG_LEVEL
```

**Expected:** API shows `debug`; the existing `env-consumer` still sees `info`. The projected file eventually shows `debug` after kubelet refresh. Timing varies by kubelet configuration and sync/cache behavior; do not assume an exact delay.

To update the environment-based consumer:

```powershell
kubectl -n ch036 delete pod env-consumer
kubectl apply -f .\ch036-env-pod.yaml
kubectl -n ch036 wait --for=condition=Ready pod/env-consumer --timeout=120s
kubectl -n ch036 exec env-consumer -- printenv LOG_LEVEL
```

**Expected:** new Pod sees `debug`. In production use a controlled Deployment rollout instead of manually deleting a standalone Pod.

## 10. Lab 6 — Rotate a dummy Secret and verify restart behavior

Change the dummy password in the lab Secret file from `not-a-real-password` to `rotated-dummy-password` and reapply it:

```powershell
kubectl apply -f .\ch036-secret.yaml
kubectl -n ch036 get secret demo-credentials -o jsonpath='{.metadata.resourceVersion}'
```

Do **not** echo the password or decode it into terminal output. Observe that a Secret mounted as a regular projected volume is eventually refreshed, but the `DB_PASSWORD` environment variable in an already-running container remains unchanged.

For the lab, recreate the environment consumer:

```powershell
kubectl -n ch036 delete pod env-consumer
kubectl apply -f .\ch036-env-pod.yaml
kubectl -n ch036 wait --for=condition=Ready pod/env-consumer --timeout=120s
kubectl -n ch036 get pod env-consumer
```

**Production rotation sequence:** prepare new credential in upstream system, distribute it through the approved secret-delivery mechanism, roll workloads safely, validate new connections, revoke old credential after a defined overlap period, and monitor authentication failures. For databases, ensure the server-side password and client rollout are coordinated. A Kubernetes Secret update alone does not rotate a database account.

## 11. Lab 7 — Inject a missing configuration key and recover

Save `ch036-broken-pod.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: broken-consumer
  namespace: ch036
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "sleep 36000"]
      env:
        - name: REQUIRED_SETTING
          valueFrom:
            configMapKeyRef:
              name: app-settings
              key: MISSING_KEY
              optional: false
```

```powershell
kubectl apply -f .\ch036-broken-pod.yaml
kubectl -n ch036 get pod broken-consumer
kubectl -n ch036 describe pod broken-consumer
kubectl -n ch036 get events --sort-by=.lastTimestamp
```

**Expected:** container cannot start and the Pod may report `CreateContainerConfigError`; events identify the missing ConfigMap key. The exact displayed status can vary.

**Targeted recovery:** add the missing non-sensitive key, then observe container startup:

```powershell
kubectl -n ch036 patch configmap app-settings --type=merge -p '{"data":{"MISSING_KEY":"ready"}}'
kubectl -n ch036 wait --for=condition=Ready pod/broken-consumer --timeout=120s
kubectl -n ch036 exec broken-consumer -- printenv REQUIRED_SETTING
```

**Expected:** `ready`. For a production application, first verify whether the key was omitted by mistake or whether the workload manifest references the wrong key. Do not fabricate an arbitrary configuration value merely to make a Pod Ready.

## 12. RBAC and security investigation

Secrets should be readable only by workloads and operators that need them. A Pod with permission to create Pods in a namespace may be able to access Secrets indirectly by mounting them, even without direct `get secrets` permission. Namespace boundaries are not complete isolation against highly privileged controllers.

Read-only access checks:

```powershell
kubectl auth can-i get secrets -n ch036
kubectl auth can-i list secrets -n ch036
kubectl auth can-i create pods -n ch036
kubectl -n ch036 get serviceaccounts
kubectl -n ch036 get rolebindings
kubectl -n ch036 get pods -o custom-columns=NAME:.metadata.name,SA:.spec.serviceAccountName
```

**Production controls:**
- Least-privilege RBAC for Secret access and workload creation.
- Encryption at rest for Kubernetes API datastore and key rotation as supported by the provider.
- External secret-management integration when appropriate, with workload identity rather than static cloud keys.
- Secret scanning in Git and CI, protected CI logs and short-lived credentials.
- Admission policies restricting privileged Pods, broad mounts and risky service accounts.
- Audit logging of Secret access without logging values.
- Restrict `kubectl exec`, debug/ephemeral containers and node-level access to authorized responders.
- Consider `immutable: true` for configuration that must not mutate; immutable objects require replacement/redeployment workflows and cannot simply be patched in place.

## 13. Production troubleshooting matrix

| Symptom | Likely cause | First checks |
|---|---|---|
| CreateContainerConfigError | Missing ConfigMap/Secret/key | Pod events, namespace, key spelling |
| App starts with old settings | Environment snapshot | Pod creation time, rollout history |
| Mounted config stale | Kubelet projection delay, subPath | Mount type, kubelet sync, app reload |
| Authentication failure after rotation | Credential mismatch or stale client | Secret version, rollout, upstream auth |
| Permission denied reading mounted file | UID/GID/mode/security context | Pod securityContext, file permissions |
| Secret absent | Wrong namespace/name or delivery failure | Secret metadata, controller status |
| Unexpected credential exposure | Excessive RBAC, logs, debug tooling | Audit events, CI logs, incident scope |
| Invalid envFrom key | Key not valid as environment name | Pod events and key format |

### Incident runbook

1. **Scope:** identify affected deployment, namespace, rollout revision and first failing Pod.
2. **Preserve evidence:** capture Pod events and metadata without dumping Secret values.
3. **Classify:** missing object, wrong key, stale environment, projected file, upstream credential or RBAC.
4. **Check references:** compare Pod `env`, `envFrom`, volume projections, object names and namespaces.
5. **Verify freshness:** compare resourceVersion and Pod creation time; inspect rollout status.
6. **Recover narrowly:** restore correct config, coordinate credential rotation, or roll workload safely.
7. **Validate:** readiness, application authentication, error rate and actual configuration behavior without printing credentials.
8. **Close:** document owner, preventive controls, rollback, and whether any credential must be revoked due to exposure.

## 14. Deployment rollout pattern

For a Deployment, an intentional restart can refresh environment-injected values:

```powershell
kubectl -n <namespace> rollout restart deployment/<deployment-name>
kubectl -n <namespace> rollout status deployment/<deployment-name> --timeout=300s
kubectl -n <namespace> rollout history deployment/<deployment-name>
```

Replace placeholders and review availability, PodDisruptionBudgets and rollout strategy before use. A `rollout restart` is not a substitute for checking that upstream credentials have been rotated and that new Pods can authenticate. Avoid using a restart as the first action when the actual failure is a missing key.

## 15. Cleanup

Only remove the dedicated disposable lab resources:

```powershell
kubectl -n ch036 get pods,configmaps,secrets
kubectl delete namespace ch036
```

Do not remove shared namespace Secrets, external secret managers, or production credentials. Delete local lab YAML containing the fake password if no longer needed, and ensure no real secrets were accidentally committed or copied into logs.

## 16. Acceptance checklist

- [ ] ConfigMap created and consumed through env and volume.
- [ ] Dummy Secret created without printing values.
- [ ] Environment variable refresh behavior demonstrated.
- [ ] Projected file update behavior observed.
- [ ] Controlled dummy Secret rotation and Pod restart performed.
- [ ] Missing-key failure reproduced and recovered.
- [ ] RBAC and Secret security limitations explained.
- [ ] Production incident and rotation runbooks reviewed.
- [ ] No real credentials entered into source control or terminal output.
- [ ] Runtime evidence and technical review completed before marking Lab Validated.

**Status:** Draft; runtime validation and technical review pending.

## 17. References

- [Kubernetes ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Distribute Credentials Securely Using Secrets](https://kubernetes.io/docs/tasks/inject-data-application/distribute-credentials-secure/)
- [Good Practices for Kubernetes Secrets](https://kubernetes.io/docs/concepts/security/secrets-good-practices/)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)

**Next:** Chapter 037 — Secret Management and Rotation.
