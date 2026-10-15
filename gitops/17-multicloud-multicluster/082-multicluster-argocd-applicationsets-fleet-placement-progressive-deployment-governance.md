# Chapter 082 — Multi-Cluster Argo CD ApplicationSets, Fleet Placement and Progressive Deployment Governance

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 17:** Multi-Cloud and Multi-Cluster GitOps  
**Chapter:** 082 / 100  
**Audience:** Platform Engineers, SREs, DevSecOps, Release Engineers and Incident Commanders

> **Safety:** Use only synthetic applications and isolated EKS, AKS and GKE staging clusters. ApplicationSet generator changes can create or remove many Applications. Inspect generated targets before applying; keep automated sync/prune disabled during initial testing. Deletion of an Application or ApplicationSet may cascade to managed resources depending on finalizers and controller settings. Protect production and stateful resources through independent approval.

## 1. Learning objectives

1. Explain ApplicationSet controller ownership and reconciliation.
2. Use cluster, list, Git directory/file and matrix generators safely.
3. Design authoritative cluster inventory and placement policy.
4. Separate environment, tenant, region and cloud provider dimensions.
5. Restrict destinations using AppProjects and Kubernetes RBAC.
6. Implement explicit rollout cohorts and promotion gates.
7. Use GitLab protected branches, CODEOWNERS and immutable digests.
8. Detect placement drift, partial rollout and stale clusters.
9. Recover from bad selectors, generated Application deletion and controller outages.
10. Measure fleet rollout SLO, change failure rate and cost.

## 2. Fleet topology

~~~text
                    GitLab protected GitOps repository
                                |
                       CI schema/policy validation
                                |
                      approved inventory metadata
                                |
                        ApplicationSet controller
                      /          |            \
                 EKS cluster  AKS cluster   GKE cluster
                     |            |            |
                 AppProject    AppProject   AppProject
                     |            |            |
                Application   Application  Application
                      \           |           /
                         rollout cohort
                                |
                       health / SLO gates
                                |
                      next cohort or rollback
~~~

ApplicationSet produces Argo CD Application resources. Argo CD reconciles each Application's desired resources. A generated Application is not proof that a workload is healthy or reachable.

## 3. Generator selection

| Generator | Use | Primary risk |
| --- | --- | --- |
| Cluster | Discover registered cluster Secrets | Untrusted labels or broad selectors |
| List | Explicit, reviewed target records | Inventory drift |
| Git directory | Generate from directory structure | Accidental new directory |
| Git file | Generate from declarative metadata | Unvalidated metadata |
| Matrix | Combine dimensions | Combinatorial explosion |
| Merge | Layer parameters with override rules | Unexpected precedence |
| Pull request | Preview environments | Untrusted source and cleanup |
| SCM provider | Repository discovery | Uncontrolled repository scope |

Check exact ApplicationSet CRD/controller version before adopting newer generator features or template semantics.

## 4. Authoritative inventory

~~~yaml
clusters:
  - id: eks-staging-us-east-1
    provider: aws
    environment: staging
    region: us-east-1
    tenant: shared
    cohort: canary
    owner: platform-sre
    approved: true
  - id: aks-staging-eastus
    provider: azure
    environment: staging
    region: eastus
    tenant: shared
    cohort: wave-2
    owner: platform-sre
    approved: true
  - id: gke-staging-us-central1
    provider: gcp
    environment: staging
    region: us-central1
    tenant: shared
    cohort: wave-2
    owner: platform-sre
    approved: true
~~~

This is a governance input, not an ApplicationSet manifest. Validate it against actual registered cluster identity, server endpoint, approval state and ownership. Cluster labels are mutable metadata, not a security boundary.

## 5. Cluster generator

~~~yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: fleet-demo-canary
  namespace: argocd
spec:
  generators:
    - clusters:
        selector:
          matchLabels:
            platform.example.com/environment: staging
            platform.example.com/cohort: canary
            platform.example.com/approved: "true"
  template:
    metadata:
      name: 'demo-{{name}}'
    spec:
      project: fleet-staging
      source:
        repoURL: https://gitlab.example.com/platform/gitops.git
        targetRevision: main
        path: apps/demo/overlays/staging
      destination:
        server: '{{server}}'
        namespace: demo-staging
      syncPolicy:
        syncOptions:
          - CreateNamespace=false
~~~

This example intentionally omits automated sync and pruning. Require reviewed cluster registration labels and an AppProject allowlist. If the local Argo CD cluster is registered and matches the selector, it may be included.

## 6. Explicit list generator

~~~yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: fleet-demo-explicit
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - clusterName: eks-staging
            server: https://REPLACE_WITH_EKS_API
          - clusterName: aks-staging
            server: https://REPLACE_WITH_AKS_API
  template:
    metadata:
      name: 'demo-{{clusterName}}'
    spec:
      project: fleet-staging
      source:
        repoURL: https://gitlab.example.com/platform/gitops.git
        targetRevision: main
        path: apps/demo/overlays/staging
      destination:
        server: '{{server}}'
        namespace: demo-staging
~~~

Explicit lists make rollout targets easy to review, but server values must be verified and access scoped. Do not copy unvalidated endpoints into production.

## 7. Git directory generator

~~~yaml
generators:
  - git:
      repoURL: https://gitlab.example.com/platform/gitops.git
      revision: main
      directories:
        - path: clusters/staging/*
~~~

This is an ApplicationSet generator fragment. A new matching directory can generate an Application; gate directory additions with schema validation and CODEOWNERS.

## 8. Git file generator

Use reviewed JSON/YAML inventory records with a defined schema. Validate required keys, unique IDs, environment restrictions and expected cluster count in CI before reconciliation.

Never let untrusted PR content control an unrestricted cluster destination, repository URL or privileged namespace.

## 9. Matrix generator

Matrix combines generator parameter sets. The resulting count can be the product of both dimensions. For example, 5 clusters × 4 apps can generate 20 Applications.

Apply bounded selectors and a CI maximum-target gate. Inspect generated names and destination tuples to prevent accidental fleet-wide deployment.

## 10. Merge generator

Use merge only when override precedence and merge keys are explicit. Keep security-critical fields such as project, destination, namespace and auto-prune policy immutable or independently validated.

## 11. Go templates and missing keys

ApplicationSet supports Go template functionality in supported versions. Enable strict missing-key checks where appropriate and test against the installed controller.

~~~yaml
spec:
  goTemplate: true
  goTemplateOptions:
    - missingkey=error
~~~

This is a fragment. Go template syntax differs from legacy template interpolation; do not mix both styles without validation.

## 12. AppProject destination restrictions

~~~yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: fleet-staging
  namespace: argocd
spec:
  sourceRepos:
    - https://gitlab.example.com/platform/gitops.git
  destinations:
    - namespace: demo-staging
      name: eks-staging
    - namespace: demo-staging
      name: aks-staging
    - namespace: demo-staging
      name: gke-staging
  clusterResourceWhitelist: []
~~~

Destination names must match registered Argo CD clusters. AppProjects do not replace Kubernetes RBAC, admission or cloud IAM.

## 13. Cluster registration governance

A cluster registration must include verified identity, approved endpoint, owner, provider, region, environment, tenant and lifecycle. Restrict mutation of Argo CD cluster Secrets.

Do not store live bearer tokens or client private keys in Git. Prefer supported short-lived/federated access or securely provisioned credentials with tested rotation and revocation.

## 14. Application naming

Use deterministic, collision-resistant names combining application, environment and cluster ID. Kubernetes object names have length and character constraints; test rendered names.

~~~text
app: demo
env: staging
cluster: eks-staging-us-east-1
generated: demo-staging-eks-staging-us-east-1
~~~

Avoid using a mutable display name as the sole identity for deletion-sensitive resources.

## 15. Placement constraints

Consider cloud provider, region, data residency, tenant, node architecture, GPU availability, storage class, network policy, image registry and application dependencies.

Use an explicit approval contract. Placement must not rely solely on an arbitrary label added by an application team.

## 16. Cohort promotion model

~~~text
CI build + tests + SBOM + signed digest
                    |
          staging canary cohort
                    |
       health / error budget / security
              /                 \
           pass                 fail
             |                    |
          wave-2              halt + revert
             |
        production canary
             |
        production wave-2
~~~

ApplicationSet does not itself guarantee cross-cluster rollout ordering. Implement waves through separate ApplicationSets/target selectors, protected Git changes or an external orchestration controller with explicit health gates.

## 17. GitLab promotion governance

Use protected branches, CODEOWNERS and merge request approvals for fleet inventory, generator logic, AppProjects, image digests and wave selectors.

Build once, promote the same signed image digest, and record actual Pod imageID on every cluster. Do not allow a pipeline with artifact-push rights to automatically mutate production cluster credentials.

## 18. Progressive rollout acceptance

A wave passes only when all expected Applications exist, Argo CD reports appropriate sync/health, synthetic checks succeed and application SLOs remain within approved thresholds.

A healthy Deployment alone is insufficient: test ingress, authentication, data dependencies, queue backlog and regional routing.

## 19. Failure budget and halt conditions

Halt promotion on unexpected target count, unauthorized destination, missing artifact signature, elevated 5xx, failed admission, unresolved OutOfSync, unknown cluster, backup failure for stateful changes or error-budget burn.

Rollback must preserve stateful data and avoid automatic deletion of PVs or databases.

## 20. Sync and pruning safety

Automated sync may be appropriate for approved low-risk workloads after tests. Automated prune and self-heal require stronger safeguards.

ApplicationSet deletion and generated Application lifecycle can interact with owner references and finalizers. Validate deletion behavior in disposable namespaces and use explicit preservation controls for stateful resources.

## 21. ApplicationSet controller observability

Monitor reconciliation errors, generated Application count, cluster discovery, controller health, API rate limits, Git repository failures and drift age.

Capture before/after target inventory and correlate ApplicationSet revision with GitLab MR and Argo CD Application status.

## 22. Provider-specific concerns

EKS: AWS IAM, VPC networking, regional capacity, IRSA/EKS Pod Identity and ECR pull. AKS: Entra identity, VNet, node pools, Azure Key Vault and ACR. GKE: Workload Identity Federation, VPC-native networking, GKE Gateway and Artifact Registry.

Keep cloud-specific StorageClasses, ingress annotations and identity configuration in provider overlays; standardize app intent and policy.

## 23. Fleet capacity and cost

Estimate per-cluster rollout surge, Pod requests, registry egress, NAT, logging and telemetry ingestion. A simultaneous fleet rollout may exhaust quotas or generate significant cross-cloud transfer charges.

Use per-wave cost and capacity checks before advancing.

## 24. Drift and break-glass changes

Document who may apply emergency imperative changes, how those changes are recorded, and how Git desired state is reconciled afterward. Never hide critical drift with broad ignoreDifferences rules.

## 25. Recovery design

Back up ApplicationSet definitions, AppProjects, repository configuration and securely recoverable cluster registrations. A recovered controller must not blindly sync every cluster before inventory, credentials and policy are revalidated.

## 26. Lab A — ApplicationSet baseline

1. Record Argo CD and ApplicationSet controller versions.
2. Inventory registered EKS, AKS and GKE staging clusters.
3. Verify AppProject and repository access.
4. Inspect current ApplicationSets.
5. Capture generated Application count.
6. Archive redacted baseline.

**Pass:** controller and fleet state are known.

## 27. Lab B — Cluster generator canary

1. Label one disposable staging cluster as canary.
2. Apply cluster generator without automated sync.
3. Inspect generated Application.
4. Verify destination and project.
5. Add second approved canary label.
6. Compare expected and actual target count.

**Pass:** discovery is deterministic.

## 28. Lab C — Explicit list generator

1. Define two approved staging endpoints.
2. Validate names and server values.
3. Apply list generator.
4. Inspect generated Applications.
5. Remove one test element.
6. Review deletion implications before reconcile.

**Pass:** explicit placement is reviewed.

## 29. Lab D — Git directory generator

1. Create disposable staging directory.
2. Add reviewed app overlay.
3. Apply generator with restricted path.
4. Inspect generated Application.
5. Introduce invalid directory fixture.
6. Confirm CI policy blocks it.

**Pass:** repository discovery is governed.

## 30. Lab E — Git file inventory

1. Define JSON/YAML schema.
2. Add approved staging cluster record.
3. Validate required fields and uniqueness.
4. Add malicious production target fixture.
5. Confirm schema/policy rejects it.
6. Restore approved inventory.

**Pass:** metadata is validated before use.

## 31. Lab F — Matrix expansion limit

1. Define two apps and two staging clusters.
2. Render matrix generator.
3. Verify four expected Applications.
4. Add synthetic excessive dimension.
5. Confirm CI max-target gate rejects change.
6. Restore bounded matrix.

**Pass:** combinatorial expansion is controlled.

## 32. Lab G — Template strictness

1. Enable supported Go template mode.
2. Add required parameter.
3. Render valid Application.
4. Remove parameter from test record.
5. Confirm missing-key error.
6. Restore valid template.

**Pass:** malformed metadata fails safely.

## 33. Lab H — AppProject destination denial

1. Restrict project to approved staging namespaces.
2. Sync permitted synthetic Application.
3. Attempt unauthorized cluster destination.
4. Confirm denial.
5. Attempt cluster-scoped privileged resource.
6. Confirm denial and record audit.

**Pass:** destination scope is enforced.

## 34. Lab I — Cluster label poisoning

1. Create disposable cluster registration.
2. Add misleading production-like label.
3. Compare against authoritative inventory.
4. Confirm admission/policy gate blocks placement.
5. Correct labels.
6. Verify target list.

**Pass:** labels cannot bypass governance.

## 35. Lab J — Canary-to-wave-2 promotion

1. Deploy signed synthetic digest to canary.
2. Confirm health, SLO and imageID.
3. Propose protected MR for wave-2.
4. Approve and reconcile.
5. Verify second cohort health.
6. Record promotion timeline.

**Pass:** wave advancement requires explicit approval.

## 36. Lab K — Failed health gate

1. Introduce synthetic 5xx regression in canary.
2. Observe SLO alert.
3. Halt wave-2 promotion.
4. Revert GitOps revision.
5. Confirm canary recovery.
6. Document stop condition.

**Pass:** unhealthy release does not spread.

## 37. Lab L — Registry portability

1. Push signed digest to approved registry.
2. Replicate to test provider registries.
3. Verify digest equivalence.
4. Deploy to EKS, AKS and GKE staging.
5. Compare Pod imageID.
6. Review pull latency and egress.

**Pass:** identical artifact runs across providers.

## 38. Lab M — Controller outage

1. Record controller state and Application count.
2. Simulate disposable controller unavailability.
3. Verify existing apps continue serving.
4. Restore controller from approved config.
5. Inspect targets before resuming sync.
6. Record recovery time.

**Pass:** outage does not trigger uncontrolled mutations.

## 39. Lab N — Application deletion safety

1. Deploy disposable stateful fixture with synthetic data.
2. Inspect owner references and finalizers.
3. Remove target from generator in a dry-run/test.
4. Verify expected deletion plan.
5. Preserve data according to policy.
6. Restore fixture and record behavior.

**Pass:** lifecycle does not destroy protected data.

## 40. Lab O — Fleet deployment incident capstone

1. Deploy synthetic app to three staging clusters.
2. Inject invalid label selector and one unhealthy cohort.
3. Observe generated Application diff and health.
4. Halt promotion and restore approved inventory.
5. Reconcile affected Applications safely.
6. Produce RCA, cost and SLO evidence.

**Pass:** fleet failure is contained and recoverable.

## 41. Troubleshooting — eighteen scenarios

| # | Symptom | Likely cause | Safe response |
| --- | --- | --- | --- |
| 1 | No generated Applications | Cluster selector mismatch | Inspect labels |
| 2 | Too many Applications | Broad selector/matrix | Halt and constrain |
| 3 | Wrong destination | Untrusted metadata | Validate inventory |
| 4 | Duplicate Application names | Naming collision | Fix template |
| 5 | Template rendering fails | Missing key | Correct schema |
| 6 | Git generator empty | Path/revision mismatch | Verify repo |
| 7 | Controller reconcile fails | CRD/version incompatibility | Check controller |
| 8 | AppProject denies sync | Destination/source restriction | Review policy |
| 9 | Remote cluster Unknown | API network/auth | Restore access |
| 10 | EKS authentication fails | AWS IAM/access | Repair scoped auth |
| 11 | AKS authentication fails | Entra/RBAC | Repair scoped auth |
| 12 | GKE authentication fails | Google IAM/plugin | Repair scoped auth |
| 13 | ImagePullBackOff | Registry/identity | Fix pull |
| 14 | Canary unhealthy | App regression | Halt promotion |
| 15 | Wave-2 starts early | Missing gate | Restore cohort control |
| 16 | Unexpected prune | Owner refs/finalizer | Protect resources |
| 17 | Drift persists | Conflicting controller | Correct ownership |
| 18 | Fleet metrics incomplete | Missing cluster labels | Repair telemetry |

## 42. Runbook — wrong fleet placement

1. Freeze affected ApplicationSet and promotions.
2. Capture generator, inventory and generated targets.
3. Identify unauthorized destinations.
4. Correct selector or inventory through reviewed Git.
5. Protect stateful resources against unintended deletion.
6. Verify expected Application count and project scope.
7. Record blast radius and RCA.

## 43. Runbook — ApplicationSet reconciliation outage

1. Identify controller, CRD and version.
2. Inspect controller logs and Kubernetes events.
3. Verify Git repository access and cluster Secrets.
4. Restore supported controller configuration.
5. Inspect generated target diff before enabling sync.
6. Validate Application health and fleet SLO.
7. Record recovery.

## 44. Runbook — progressive rollout regression

1. Identify affected cohort, digest and GitLab MR.
2. Halt subsequent wave changes.
3. Compare synthetic checks and SLO against baseline.
4. Revert approved GitOps revision.
5. Verify imageID and service health.
6. Preserve database/PVC state.
7. Document failure and prevention.

## 45. Runbook — remote cluster authentication failure

1. Identify provider, cluster, owner and endpoint.
2. Verify DNS/TLS/private routing.
3. Inspect cloud identity federation or scoped credentials.
4. Validate Kubernetes RBAC.
5. Restore least-privilege access and rotate if needed.
6. Verify dry-run sync.
7. Archive audit evidence.

## 46. Runbook — accidental Application deletion

1. Stop further generator changes and pruning.
2. Capture deleted Application and managed resource inventory.
3. Inspect finalizers and orphaned resources.
4. Restore approved generator configuration.
5. Recreate missing stateless resources safely.
6. Recover stateful data only from verified backups if required.
7. Record impact and add lifecycle guardrails.

## 47. Evidence template

~~~text
Change/incident ID:
GitLab MR and immutable artifact digest:
ApplicationSet controller and CRD version:
Generator type, selectors and template:
Authoritative cluster inventory revision:
Expected/actual Application count:
AppProject source/destination restrictions:
Cohort/wave and health gates:
EKS/AKS/GKE registration and RBAC:
Application sync, health and imageID:
Observed SLO, errors and drift:
Deletion/finalizer/prune review:
Rollback, approval and cost evidence:
~~~

## 48. Scored operational readiness

| Domain | Points | Evidence |
| --- | ---: | --- |
| Inventory and generator design | 20 | Bounded expected targets |
| AppProject and identity isolation | 20 | Denied unauthorized destinations |
| Promotion and health gates | 20 | Canary and wave-2 evidence |
| Artifact provenance and portability | 10 | Signed digest and imageID |
| Deletion, drift and rollback safety | 20 | Recovery rehearsals |
| Observability and ownership | 10 | Metrics and runbooks |
| **Total** | **100** | |

**Pass:** at least 85/100 and no critical failure: uncontrolled production targeting, unsafe pruning, unauthorized AppProject destination, unreviewed fleet-wide rollout or missing recovery path.

## 49. Final acceptance checklist

- [ ] ApplicationSet version and CRDs verified.
- [ ] Fleet inventory and cluster registration approved.
- [ ] Cluster/list/Git generator behavior tested.
- [ ] Matrix expansion and template validation bounded.
- [ ] AppProjects enforce destination restrictions.
- [ ] EKS/AKS/GKE remote identities least-privileged.
- [ ] Cluster labels verified against source of truth.
- [ ] GitLab protected MR promotion enabled.
- [ ] Immutable signed digest deployed.
- [ ] Canary and wave-2 health gates validated.
- [ ] SLO-based halt and rollback tested.
- [ ] Stateful pruning and finalizer behavior reviewed.
- [ ] Controller outage recovery rehearsed.
- [ ] Fifteen hands-on labs completed.
- [ ] Eighteen troubleshooting scenarios reviewed.
- [ ] Five production runbooks validated.
- [ ] 100-point readiness assessment signed off.

## 50. Knowledge check

1. How do cluster and list generators differ in governance risk?
2. Why can a matrix generator cause a deployment explosion?
3. What prevents cluster label spoofing from becoming a production deployment?
4. Why does ApplicationSet not guarantee ordered rollout waves?
5. How should AppProjects and Kubernetes RBAC complement one another?
6. Why should artifact digest remain unchanged between cohorts?
7. What are safe halt conditions for progressive fleet rollout?
8. How do finalizers and pruning affect Application deletion?
9. Why is Argo CD Healthy not sufficient to pass an SLO gate?
10. How would you restore a controller without immediately syncing unsafe targets?

## 51. References

- [Argo CD ApplicationSet](https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/)
- [ApplicationSet generators](https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/Generators/)
- [ApplicationSet cluster generator](https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/Generators-Cluster/)
- [ApplicationSet Git generator](https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/Generators-Git/)
- [ApplicationSet matrix generator](https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/Generators-Matrix/)
- [Argo CD AppProjects](https://argo-cd.readthedocs.io/en/stable/user-guide/projects/)
- [Argo CD sync options](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/)
- [GitLab protected branches](https://docs.gitlab.com/user/project/repository/branches/protected/)
- [GitLab CI/CD](https://docs.gitlab.com/ci/)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)

---

**Chapter 082 complete.** Next: **Chapter 083 — Multi-Cloud Workload Identity, Secrets, Network Security and Policy Enforcement**.