# Chapter 096 — CRDs, Operators and Custom Controllers

**Track:** Kubernetes Administration · **Part 20 — Advanced Platform Engineering and Production Operations**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** Kubernetes administrators, SREs, platform engineers, operator developers  
**Prerequisites:** Chapters 011–015, 036–045, 091–095; kubectl, PowerShell, Git, a disposable Kubernetes cluster; optional Go/Operator SDK or Kubebuilder environment.

## Learning outcomes

Explain the Kubernetes API extension model; create and validate a CRD and custom resources; distinguish controllers from operators; understand reconciliation, status, conditions, finalizers and owner references; inspect controller RBAC, leader election and health; plan CRD upgrades and conversions; investigate incidents and recover safely.

## 1. Architecture: desired state and reconciliation

```text
User / GitOps
    |
    v
Custom Resource (desired state) → API server → etcd
                                      |
                                  watch/list
                                      |
                                      v
                                Controller
                               reconcile loop
                                 |       |
                              observe   act
                                 |       |
                                 v       v
                         Deployment, Service,
                         Job, ConfigMap, etc.
                                 |
                                 v
                           status/conditions
```

A **CustomResourceDefinition (CRD)** registers a new API resource type. A **Custom Resource (CR)** is an instance of that type. A **controller** observes resources and acts to move observed state toward desired state. An **operator** packages domain-specific operational logic, commonly using CRDs and controllers, for tasks such as database provisioning, upgrades, backups and failover.

A CRD alone does **not** provision workloads. It only adds API storage, discovery and validation. The controller supplies behavior.

## 2. Key API design principles

- Use a stable API group, meaningful plural/singular/kind names and a versioning plan.
- Define structural OpenAPI v3 schemas with validation and clear defaults.
- Keep `spec` as user intent and `status` as controller-observed state.
- Use `status.observedGeneration` and conditions to distinguish current from stale status.
- Reconcile idempotently; tolerate repeated events and partial failures.
- Use exponential retry/backoff, avoid hot loops and expose controller health metrics.
- Grant only required RBAC verbs and scopes.
- Plan deletion, finalizer behavior and data retention before deployment.
- Prefer Kubernetes native primitives where a CRD is not necessary.

## 3. Lab 01 — Discover installed API extensions

```powershell
kubectl config current-context
kubectl api-resources
kubectl get crds
kubectl get apiservices
kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations
kubectl get deployments -A
```

Inspect one known CRD from the current cluster:

```powershell
kubectl describe crd <crd-name>
kubectl get crd <crd-name> -o yaml
```

Replace the placeholder with a real name. Do not delete CRDs in shared environments: deleting a CRD removes all custom resources of that type and can cause data loss.

**Acceptance:** distinguish CRDs, aggregated API services and admission webhooks; record versions, served/storage versions and owners.

## 4. Lab 02 — Define a safe sample CRD

The example `AppConfig` CRD is a teaching resource; no controller is installed by this lab.

Save as `appconfig-crd.yaml`:

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: appconfigs.platform.example.com
spec:
  group: platform.example.com
  scope: Namespaced
  names:
    plural: appconfigs
    singular: appconfig
    kind: AppConfig
    shortNames: [acfg]
  versions:
  - name: v1alpha1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            required: [replicas, image]
            properties:
              replicas:
                type: integer
                minimum: 0
                maximum: 5
              image:
                type: string
                minLength: 1
          status:
            type: object
            properties:
              observedGeneration:
                type: integer
                format: int64
              readyReplicas:
                type: integer
                minimum: 0
              conditions:
                type: array
                x-kubernetes-list-type: map
                x-kubernetes-list-map-keys: [type]
                items:
                  type: object
                  required: [type, status, lastTransitionTime, reason, message]
                  properties:
                    type:
                      type: string
                    status:
                      type: string
                      enum: ["True", "False", "Unknown"]
                    lastTransitionTime:
                      type: string
                      format: date-time
                    reason:
                      type: string
                    message:
                      type: string
    subresources:
      status: {}
```

```powershell
kubectl apply --dry-run=server -f .\appconfig-crd.yaml
kubectl apply -f .\appconfig-crd.yaml
kubectl wait --for=condition=Established crd/appconfigs.platform.example.com --timeout=60s
kubectl api-resources --api-group=platform.example.com
```

Use a disposable cluster: CRDs are **cluster-scoped** even if their instances are namespaced.

## 5. Lab 03 — Create and validate a custom resource

Save as `appconfig-sample.yaml`:

```yaml
apiVersion: platform.example.com/v1alpha1
kind: AppConfig
metadata:
  name: demo
  namespace: default
spec:
  replicas: 2
  image: nginx:1.27
```

```powershell
kubectl apply --dry-run=server -f .\appconfig-sample.yaml
kubectl apply -f .\appconfig-sample.yaml
kubectl get appconfigs -A
kubectl explain appconfig.spec --api-version=platform.example.com/v1alpha1
kubectl get appconfig demo -o yaml
```

Try an invalid `replicas: 10` in a copy of the manifest and verify schema validation rejects it. Confirm no Deployment is created automatically: a CRD without a controller has no reconciliation logic.

## 6. Lab 04 — Understand spec, status and generations

```powershell
kubectl get appconfig demo -o jsonpath='{.metadata.generation}'
kubectl get appconfig demo -o jsonpath='{.status.observedGeneration}'
kubectl get appconfig demo -o jsonpath='{.status.conditions}'
```

In this controller-free example, status remains empty. A real controller writes to the `status` subresource using separate authorization and reports the generation it observed. Conditions should carry a stable `type`, a `True/False/Unknown` status, a meaningful reason, message and transition timestamp. Do not interpret an old `Ready=True` condition as current if `observedGeneration` lags behind metadata generation.

## 7. Lab 05 — Reconciliation algorithm walkthrough

A typical controller loop:

```text
Reconcile(key):
  fetch AppConfig
  if NotFound: return
  if deleting:
      perform bounded, idempotent cleanup
      remove owned finalizer only when cleanup is complete
      return
  validate dependencies and desired state
  ensure owned Deployment exists with correct spec
  ensure owned Service exists with correct spec
  observe Deployment status
  update CR status/conditions and observedGeneration
  return; retry transient errors with backoff
```

Avoid an unconditional update on every reconciliation: it creates self-triggered event storms. Use optimistic concurrency and re-fetch on conflicts. Account for eventual consistency between caches and API writes. Do not blindly overwrite user-owned fields on shared resources.

## 8. Lab 06 — Owner references and garbage collection

```powershell
kubectl get deployment -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"/"}{.metadata.name}{" owners="}{.metadata.ownerReferences[*].kind}{"\n"}{end}'
kubectl get events -A --sort-by=.lastTimestamp
```

Owner references express dependency relationships for garbage collection; they are not the same as finalizers. Namespaced dependents must respect owner-reference namespace rules, and cluster-scoped dependents cannot validly point to namespaced owners. Evaluate foreground/background/orphan deletion semantics before making an operator own resources containing durable data.

**Exercise:** inspect owner references on a disposable Deployment managed by an existing controller; record the ReplicaSet relationship. Do not edit production owner references.

## 9. Lab 07 — Finalizers and deletion lifecycle

A finalizer causes deletion to set `metadata.deletionTimestamp` while the API object remains until the finalizer is removed. Controllers must perform cleanup safely and remove **only their own** finalizers when appropriate.

```powershell
kubectl get appconfig demo -o jsonpath='{.metadata.finalizers}'
kubectl get appconfig demo -o jsonpath='{.metadata.deletionTimestamp}'
kubectl describe appconfig demo
```

**Do not add an arbitrary finalizer to the sample CR unless you also have a working controller to remove it.** Force-removing finalizers can orphan external resources or violate backup/data-retention guarantees. For stuck deletions, investigate controller health, logs, cloud dependencies and cleanup progress before any manual intervention.

## 10. Lab 08 — Controller deployment and RBAC

An operator usually runs as a Deployment with a dedicated ServiceAccount. It needs `get/list/watch` on its CRs, `update/patch` on the CR status subresource, and narrow verbs on managed workloads. Some operators also require leader-election permissions on coordination Lease objects.

```powershell
kubectl get serviceaccounts -A
kubectl get clusterroles,clusterrolebindings
kubectl get leases -A
kubectl auth can-i update appconfigs/status -n default --as=system:serviceaccount:default:example-operator
```

The example service account is not created by this chapter; the authorization check will be negative or error unless you install one. Use the actual operator identity when evaluating a real installation. Review permissions to read Secrets, mutate webhooks or create cluster-scoped resources as high risk.

## 11. Lab 09 — Operator installation and lifecycle

Choose a disposable, noncritical operator from your organization's approved catalog, or use a local Kubebuilder/Operator SDK example with pinned versions. Before installing, inventory:
- CRDs and their schema/versions.
- Controller Deployments and ServiceAccounts.
- ClusterRoles, Roles and bindings.
- Admission/conversion webhooks and certificates.
- Required metrics, health probes and leader election.
- Supported Kubernetes versions and upgrade paths.
- Data ownership and uninstall behavior.

```powershell
helm list -A
kubectl get crds
kubectl get pods -A
kubectl get events -A --sort-by=.lastTimestamp
```

**Acceptance:** the operator becomes healthy and reconciles one approved disposable custom resource. Installation alone does not demonstrate correct reconciliation.

## 12. Lab 10 — Controller observability

Inspect logs and metrics from the chosen operator:

```powershell
kubectl get deployments -A
kubectl logs -n <operator-namespace> deployment/<operator-deployment> --since=15m
kubectl describe deployment <operator-deployment> -n <operator-namespace>
kubectl get events -n <operator-namespace> --sort-by=.lastTimestamp
```

Replace placeholders. Useful SLIs: reconciliation success/failure rate, reconcile duration, queue depth, retry count, stale `observedGeneration`, unavailable replicas, webhook latency and leader election transitions. Alert on sustained reconciliation failure rather than every harmless retry. Avoid high-cardinality CR identifiers in metrics.

## 13. Lab 11 — Failure injection and recovery

In a disposable environment, create a CR referring to an unavailable dependency or invalid workload image and observe controller status and events. Do not disable a production operator or remove its permissions.

Record:
1. Initial CR generation and desired state.
2. Controller's reconciliation error and condition.
3. Event/log evidence and alert latency.
4. Corrective Git change.
5. Convergence time and final `observedGeneration`.
6. Any orphaned or partially created resources.

A controller crash may leave existing workloads running but prevent future updates and recovery; this is a separate failure mode from application unavailability.

## 14. Lab 12 — CRD versioning and conversion

Distinguish:
- **Served version:** accepted by the API endpoint.
- **Storage version:** used to persist objects in etcd.
- **Conversion:** translating between API versions; complex changes may require a conversion webhook.
- **Stored versions:** historical versions listed in CRD status until migration and status cleanup are properly completed.

```powershell
kubectl get crd appconfigs.platform.example.com -o jsonpath='{.spec.versions}'
kubectl get crd appconfigs.platform.example.com -o jsonpath='{.status.storedVersions}'
```

Do not simply flip `storage: true` for an incompatible schema or remove an old served version without migration planning. Back up custom resources and relevant external state; rehearse conversion-webhook outage and rollback in staging.

## 15. Lab 13 — GitOps and operator interactions

Operators and GitOps controllers are **both** reconcilers. Prevent competing ownership:
- GitOps typically owns the CRD/operator installation and declarative custom-resource `spec`.
- The operator owns generated child objects and custom-resource `status`.
- GitOps diff configuration may need to ignore operator-managed fields, with narrowly scoped justification.
- Avoid GitOps pruning a CRD while live CRs remain.
- Sequence CRD upgrades, controller upgrades and CR schema changes carefully.

**Exercise:** make an approved custom-resource spec change through Git and observe operator reconciliation. Confirm GitOps does not continually revert operator-written status or child-object defaults.

## 16. Lab 14 — Security and supply-chain review

Check controller image provenance, digest pinning, RBAC least privilege, network egress, ServiceAccount tokens, webhook certificates, pod security, admission failure policies, vulnerability scanning and release support.

Questions for review:
- Can the operator read Secrets across namespaces?
- Does it create cluster-wide roles or webhooks?
- Does it require privileged containers or host access?
- Can a tenant's custom resource cause actions in another namespace?
- Are externally managed cloud resources created or deleted?
- Are status messages safe from credential leakage?

Test authorization and admission boundaries before granting tenant access to a powerful CRD.

## 17. Lab 15 — Upgrade and rollback rehearsal

On a disposable cluster, document:
1. Installed operator and CRD versions.
2. Supported Kubernetes compatibility.
3. CRD schema and storage-version changes.
4. Controller Deployment rollout strategy.
5. Backup/restore of CRs and external state.
6. Webhook availability and certificate rotation.
7. Forward and backward compatibility limits.
8. Recovery path if the old controller cannot read new CRs.

Run the vendor-supported upgrade path and validate existing CRs, controller health and child resources. **Helm rollback alone may not revert CRDs or persisted custom-resource schema/data.** Treat rollback as a separately tested plan.

## 18. Lab 16 — Production-style troubleshooting runbook

| Symptom | Inspect | Typical root cause | Safe response |
|---|---|---|---|
| `no matches for kind` | CRD existence, served versions, API discovery | CRD missing/version mismatch | Install correct CRD first |
| CR exists but nothing happens | Controller Pods, watches, logs, RBAC | Controller absent/unhealthy | Restore controller and permissions |
| CR `Ready` stale | Generation vs observedGeneration | Reconcile stalled | Investigate queue/errors |
| Object stuck Terminating | Finalizers, deletionTimestamp, logs | Cleanup blocked | Repair cleanup dependency |
| API request hangs/rejects | Webhook endpoints, certs, failurePolicy | Admission/conversion webhook outage | Follow approved recovery |
| Operator upgrade breaks CRs | Storage versions, schemas, release notes | Incompatible version transition | Use tested migration/rollback |
| Reconcile loop high CPU | Logs, events, write frequency | Unconditional writes/hot retry | Fix controller logic/backoff |
| Child objects unexpectedly change | ownerRefs, managedFields, GitOps | Competing reconcilers | Clarify field ownership |

## 19. Operational acceptance

- [ ] CRD group, scope, kind, schema and versions reviewed.
- [ ] Valid CR accepted; invalid CR rejected by schema.
- [ ] Controller-free CR does not falsely appear reconciled.
- [ ] Real controller reconciliation observed with current status.
- [ ] RBAC, ServiceAccount and cluster-scoped permissions reviewed.
- [ ] Owner references, garbage collection and finalizers understood.
- [ ] Controller logs, metrics and actionable alerts verified.
- [ ] Failure and recovery simulation completed in staging.
- [ ] CRD upgrade/conversion and rollback risks documented.
- [ ] GitOps ownership conflicts tested.
- [ ] Supply-chain and tenant isolation review completed.
- [ ] Runtime evidence and independent technical review recorded.

## 20. Cleanup

**Only in the disposable lab cluster**, and only if no other workload uses this teaching CRD:

```powershell
kubectl delete appconfig demo --ignore-not-found
kubectl delete -f .\appconfig-crd.yaml
```

Deleting a CRD deletes all instances of its kind; verify the complete inventory first. Do not uninstall a production operator or delete its CRDs merely to clean up tutorial artifacts. Preserve required backups and audit evidence.

## Production takeaways

CRDs extend the API; controllers provide behavior; operators automate domain-specific operations. Treat controllers as privileged production software with explicit RBAC, ownership, observability, upgrade, backup and recovery procedures. A healthy Deployment is not enough: verify convergence and fresh status for the managed custom resources.

**Draft status:** examples and labs are written but have not been runtime-validated or independently reviewed.

**Next:** Chapter 097 — GPU Scheduling and AI Workloads.
