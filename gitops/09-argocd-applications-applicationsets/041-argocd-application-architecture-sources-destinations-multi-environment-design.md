# Chapter 041 — Argo CD Application Architecture, Sources, Destinations and Multi-Environment Design

**Part 09 — Argo CD Applications and ApplicationSets** | **Chapter 041 of 100**  
**Audience:** SREs, platform engineers, Kubernetes administrators  
**Prerequisites:** Chapters 036–040, Helm Part 07, GitLab CI/CD foundations  
**Lab environment:** One Kubernetes cluster with namespaces \`demo-dev\`, \`demo-test\`, \`demo-staging\`, \`demo-prod\`; Argo CD control plane in \`argocd\`.

> **Safety:** Run write exercises only in an approved disposable cluster or namespace. Keep production Applications manual-sync, with pruning and self-heal disabled until formally approved. Example GitLab URLs and image digests are placeholders. Never commit credentials or use customer-specific application names.

## 1. Objectives

By the end, you can:

1. Model Argo CD Applications as source-to-destination declarations.
2. Explain the differences among Application, AppProject and ApplicationSet.
3. Select Git, Helm repository, OCI and Kustomize sources appropriately.
4. Design four independently governed environments in a single Kubernetes cluster.
5. Use chart-local Helm values overlays and immutable image digests.
6. Explain single-source and multiple-source Application constraints.
7. Define AppProject source/destination/resource restrictions.
8. Avoid application ownership collisions, uncontrolled pruning and dangerous deletion.
9. Validate Applications offline and in an authorized cluster.
10. Diagnose source, destination, render and reconciliation failures.

## 2. Enterprise architecture

\`\`\`text
GitLab application repository
     |  CI build/test/scan/sign once
     v
Approved OCI image@sha256:<digest>
     |
Reviewed GitOps configuration repository
     |
Argo CD repository server -> render chart + values
     |
Argo CD Application controller -> compare desired/live
     |
Kubernetes API: ONE cluster
     |
+----------------+----------------+------------------+---------------+
| demo-dev       | demo-test      | demo-staging     | demo-prod     |
| demo-app-dev   | demo-app-test  | demo-app-staging | demo-app-prod |
+----------------+----------------+------------------+---------------+
\`\`\`

The four environments are **separate namespaces in the same cluster**, not separate clusters. Their Application objects live in the Argo CD control-plane namespace and point to distinct destination namespaces. Production may need independent cluster isolation when required by risk and compliance.

## 3. Argo CD object model

| Object | Purpose | Typical owner |
| --- | --- | --- |
| \`Application\` | Defines desired source, destination, project and sync policy | Application/platform team |
| \`AppProject\` | Restricts allowed repositories, destinations, resource kinds and roles | Platform security team |
| \`ApplicationSet\` | Generates Applications from generators/templates | Platform automation team |
| \`Secret\` (repository) | Provides Git/registry access | Approved secret controller |
| Kubernetes workloads | Live resources reconciled by Application controller | Argo CD under authorized RBAC |

A Project is a policy boundary, not a namespace. An ApplicationSet is a generator, not a replacement for the Application reconciliation controller.

## 4. Application specification anatomy

\`\`\`yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: demo-app-dev
  namespace: argocd
spec:
  project: demo-platform
  source:
    repoURL: https://gitlab.example.com/platform/demo-gitops.git
    targetRevision: main
    path: charts/demo-app
    helm:
      valueFiles:
        - env/dev-values.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: demo-dev
  syncPolicy:
    syncOptions:
      - CreateNamespace=false
\`\`\`

Important fields:

- \`metadata.name\`: unique Application name in the Argo CD namespace.
- \`spec.project\`: required authorization policy.
- \`spec.source.repoURL\`: repository containing desired configuration.
- \`spec.source.targetRevision\`: branch, tag or commit (or chart version for a chart source).
- \`spec.source.path\`: path for a Git directory/chart.
- \`spec.source.helm.valueFiles\`: chart-relative values files for a single-source Git chart.
- \`spec.destination.server\`: target cluster API identifier.
- \`spec.destination.namespace\`: target namespace for namespaced resources.
- \`spec.syncPolicy\`: sync behavior; this example is manual-sync.

Argo CD can track a branch like \`main\` to follow reviewed Git changes, while promotion evidence must capture the exact resolved commit. Pin production artifact/image digests, not mutable image tags.

## 5. Source types and selection

| Source type | Typical configuration | Operational consideration |
| --- | --- | --- |
| Git directory of YAML | \`repoURL\`, \`targetRevision\`, \`path\` | No templating unless configured |
| Git-hosted Helm chart | Git URL + chart directory \`path\` | Values files resolve against chart path |
| Helm chart repository | Repository URL + \`chart\` + chart version | Verify chart provenance and pin version |
| OCI Helm chart | OCI-capable chart source | Registry credentials and version/digest policy |
| Kustomize | Git path with \`kustomization.yaml\` | Overlay drift and patch order |
| Multiple sources | \`spec.sources\` array | Cross-repo values and collision risks |

For Helm chart repositories, \`targetRevision\` typically selects the chart version. For Git, it selects the Git ref. Do not confuse the chart's \`appVersion\` with the deployable container image digest.

## 6. Recommended GitOps repository layout

\`\`\`text
demo-gitops/
├── charts/
│   └── demo-app/
│       ├── Chart.yaml
│       ├── Chart.lock
│       ├── values.yaml
│       ├── values.schema.json
│       ├── env/
│       │   ├── dev-values.yaml
│       │   ├── test-values.yaml
│       │   ├── staging-values.yaml
│       │   └── prod-values.yaml
│       └── templates/
│           ├── deployment.yaml
│           ├── service.yaml
│           ├── configmap.yaml
│           └── _helpers.tpl
├── argocd/
│   ├── projects/demo-platform.yaml
│   └── applications/
│       ├── demo-app-dev.yaml
│       ├── demo-app-test.yaml
│       ├── demo-app-staging.yaml
│       └── demo-app-prod.yaml
└── docs/
    ├── promotion-policy.md
    └── recovery-runbook.md
\`\`\`

This initial layout keeps all Helm values within the chart directory. Later chapters will demonstrate multiple sources for separating chart and environment values repositories.

## 7. Values overlays and immutable images

Example \`charts/demo-app/values.yaml\`:

\`\`\`yaml
image:
  repository: registry.example.com/platform/demo-app
  digest: "sha256:REPLACE_WITH_VERIFIED_64_HEX_DIGEST"
replicaCount: 2
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    memory: 512Mi
\`\`\`

Example \`charts/demo-app/env/dev-values.yaml\`:

\`\`\`yaml
replicaCount: 1
environment: dev
\`\`\`

Example \`charts/demo-app/env/prod-values.yaml\`:

\`\`\`yaml
replicaCount: 3
environment: prod
\`\`\`

Your Deployment template should reference \`repository@digest\` and validate that the digest is real. The placeholder above is intentionally not a deployable digest. Do not set environment-specific mutable image tags.

During a controlled promotion, each environment values file may temporarily reference its last approved image digest; after all gates pass, they converge on the same newly approved digest.

## 8. AppProject governance

\`argocd/projects/demo-platform.yaml\`:

\`\`\`yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: demo-platform
  namespace: argocd
spec:
  description: Approved demo application sources and namespaces
  sourceRepos:
    - https://gitlab.example.com/platform/demo-gitops.git
  destinations:
    - server: https://kubernetes.default.svc
      namespace: demo-dev
    - server: https://kubernetes.default.svc
      namespace: demo-test
    - server: https://kubernetes.default.svc
      namespace: demo-staging
    - server: https://kubernetes.default.svc
      namespace: demo-prod
  clusterResourceWhitelist: []
  namespaceResourceBlacklist:
    - group: rbac.authorization.k8s.io
      kind: Role
    - group: rbac.authorization.k8s.io
      kind: RoleBinding
\`\`\`

A Project's allowed destinations do not grant permission to the underlying Argo CD controller ServiceAccount. Kubernetes RBAC and admission policies must independently enforce least privilege.

## 9. Four Application manifests

**Dev:**

\`\`\`yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: demo-app-dev
  namespace: argocd
spec:
  project: demo-platform
  source:
    repoURL: https://gitlab.example.com/platform/demo-gitops.git
    targetRevision: main
    path: charts/demo-app
    helm:
      valueFiles: [env/dev-values.yaml]
  destination:
    server: https://kubernetes.default.svc
    namespace: demo-dev
  syncPolicy:
    syncOptions: [CreateNamespace=false]
\`\`\`

Use identical structure for the other environments with these replacements:

| Application | \`metadata.name\` | \`valueFiles\` | Destination |
| --- | --- | --- | --- |
| Test | \`demo-app-test\` | \`env/test-values.yaml\` | \`demo-test\` |
| Staging | \`demo-app-staging\` | \`env/staging-values.yaml\` | \`demo-staging\` |
| Production | \`demo-app-prod\` | \`env/prod-values.yaml\` | \`demo-prod\` |

Keep sync manual until the team's governance policy authorizes automation. Avoid applying all four Applications to a live cluster as an introductory lab.

## 10. Lab A — Offline render and compare

From a trusted Git checkout:

\`\`\`bash
helm dependency build charts/demo-app
helm lint charts/demo-app
helm template demo-app charts/demo-app \
  --namespace demo-dev \
  -f charts/demo-app/env/dev-values.yaml > dev-rendered.yaml
helm template demo-app charts/demo-app \
  --namespace demo-test \
  -f charts/demo-app/env/test-values.yaml > test-rendered.yaml
helm template demo-app charts/demo-app \
  --namespace demo-staging \
  -f charts/demo-app/env/staging-values.yaml > staging-rendered.yaml
helm template demo-app charts/demo-app \
  --namespace demo-prod \
  -f charts/demo-app/env/prod-values.yaml > prod-rendered.yaml
\`\`\`

Validate namespace, Service selectors, workload labels, security context, probes, resource limits, replica count, image digest and forbidden cluster-scoped resources. Offline render is not proof of Kubernetes admission or health.

## 11. Lab B — Application validation

Read-only preflight:

\`\`\`bash
kubectl config current-context
kubectl get namespace argocd demo-dev demo-test demo-staging demo-prod
kubectl get appprojects.argoproj.io -n argocd
kubectl get applications.argoproj.io -n argocd
\`\`\`

For a disposable cluster with approved permissions:

\`\`\`bash
kubectl apply --dry-run=client -f argocd/projects/demo-platform.yaml
kubectl apply --dry-run=client -f argocd/applications/demo-app-dev.yaml
\`\`\`

If the Argo CD CRDs are installed and server-side dry run is authorized, also validate against the API server:

\`\`\`bash
kubectl apply --dry-run=server -f argocd/applications/demo-app-dev.yaml
\`\`\`

Server dry run checks admission but does not prove the repo URL, chart path or credentials are valid.

## 12. Lab C — Deploy Dev through manual sync

Only after review:

\`\`\`bash
kubectl apply -f argocd/projects/demo-platform.yaml
kubectl apply -f argocd/applications/demo-app-dev.yaml
argocd app get demo-app-dev
argocd app diff demo-app-dev
\`\`\`

Review the diff for deletions, namespace violations and ownership conflicts. If approved:

\`\`\`bash
argocd app sync demo-app-dev
argocd app wait demo-app-dev --sync --health --timeout 300
kubectl get deployment,pods,svc -n demo-dev
kubectl get endpointslices -n demo-dev
\`\`\`

Record the exact Git commit, image digest, Helm chart version, Argo CD sync/health and HTTP SLI checks.

## 13. Multi-source Applications

Argo CD supports \`spec.sources\` for use cases such as a Helm chart from one source and values from another Git repository. A simplified conceptual pattern:

\`\`\`yaml
spec:
  sources:
    - repoURL: https://charts.example.com
      chart: demo-app
      targetRevision: 1.2.3
      helm:
        valueFiles:
          - $values/environments/dev/values.yaml
    - repoURL: https://gitlab.example.com/platform/demo-values.git
      targetRevision: main
      ref: values
\`\`\`

**Important:** The \`$values\` reference must correspond to a source with \`ref: values\`; its file path is resolved from the root of that values repository. Do not add \`chart\` to a source used solely for \`ref\`. Validate your Argo CD release's multiple-source support and collision handling.

Use multiple sources sparingly; they are not a substitute for ApplicationSet generators when managing many Applications.

## 14. Ownership and collision prevention

Two Applications should not manage the same Kubernetes resource. Collision risks include:

- Same namespace, kind and name from two Helm charts.
- Shared ConfigMaps or Secrets rendered by multiple Applications.
- One Application prunes an object another depends on.
- Two controllers (Helm CLI and Argo CD) managing the same Deployment.
- Unintended namespace or cluster-scoped resources in a chart.

Enable and review Argo CD shared-resource detection where appropriate. A useful safety option is \`FailOnSharedResource=true\`, but confirm behavior and compatibility with the installed release. Ownership must be reviewed before automated pruning.

## 15. Resource tracking and deletion behavior

Argo CD tracks managed resources through supported label/annotation mechanisms. Choose a tracking strategy consistent with the installed version and avoid modifying tracking identifiers manually.

Be especially cautious with:

- Application deletion finalizers and cascading deletion.
- \`prune\` and \`allowEmpty\` settings.
- Namespace deletion.
- PersistentVolumeClaim retention.
- Shared CRDs and cluster-scoped resources.
- Orphaned resources and false ownership matches.

**Rule:** Do not use an Application deletion as an informal rollback. Revert the GitOps desired state and reconcile safely.

## 16. Sync and health are independent

| Sync | Health | Meaning |
| --- | --- | --- |
| Synced | Healthy | Desired/live agreement and healthy resource assessments |
| Synced | Degraded | Desired configuration applied, workload unhealthy |
| OutOfSync | Healthy | Live drift or pending desired change, workload still healthy |
| OutOfSync | Missing | Resource absent or pending creation |
| Unknown | Unknown | Comparison/health unavailable or indeterminate |

Argo CD health is not an application SLO. Verify HTTP error rate, latency, availability and dependency behavior after any promotion.

## 17. Troubleshooting matrix

| Symptom | Likely cause | First checks |
| --- | --- | --- |
| App cannot load source | Bad Git URL/ref/credentials | repo-server, auth, DNS, TLS |
| Helm render fails | Missing values/dependency/schema | \`helm lint\`, \`helm template\` |
| Destination denied | AppProject restrictions | allowed destinations |
| Kubernetes forbidden | Controller RBAC | ServiceAccount bindings |
| OutOfSync forever | Pending manual sync or drift | diff, revision, policy |
| Synced but Degraded | Runtime failure | Pods, probes, image pull, Service |
| Wrong environment config | Incorrect values file | Application source and render |
| Shared resource warning | Ownership collision | tracking and resource names |
| Unexpected deletion candidate | Prune/desired state | diff, finalizers, PVC policy |
| Multi-source values missing | Wrong \`$values\` path or ref | source refs and repo layout |

Do not grant cluster-admin or disable TLS as a shortcut.

## 18. Failure-injection lab (disposable only)

Perform at least three:

1. Change the Git source path to a nonexistent chart directory; capture comparison error; restore it.
2. Reference a nonexistent values file; observe manifest-generation failure; correct the file path.
3. Target an unauthorized namespace; verify AppProject rejection; restore approved destination.
4. Deliberately choose a duplicate resource name in a dry-run render; identify ownership risk before sync.
5. Simulate an unavailable image digest in disposable Dev; verify Degraded health and GitOps recovery.

Capture the failure, root cause, recovery and absence of production impact. Never test pruning by deleting shared resources.

## 19. Incident runbook — Wrong environment values deployed

**Scenario:** A Dev Application unexpectedly renders production-sized replicas and a production-only setting.

1. Stop further promotions and confirm cluster context.
2. Inspect Application \`source.path\`, \`helm.valueFiles\`, Git commit and chart version.
3. Render the chart offline with the expected Dev values.
4. Compare Argo CD desired manifests and live resources.
5. Check whether the wrong values were merged or Application configuration was changed.
6. Revert the incorrect GitOps commit through an approved MR.
7. Reconcile Dev and verify expected replicas, endpoints and SLIs.
8. Add CI validation for environment-to-values mapping.
9. Document blast radius, detection, recovery time and preventive controls.

## 20. EKS, AKS and GKE alignment

The Application model is the same across EKS, AKS and GKE. Provider differences affect identity, registry credentials, networking, ingress, storage and admission. This chapter uses a **single cluster at a time**; later chapters cover provider-specific GitOps and multi-cluster fleets.

| Capability | EKS | AKS | GKE |
| --- | --- | --- | --- |
| Workload identity | Pod Identity/IRSA | Entra Workload ID | Workload Identity Federation |
| Image registry | ECR | ACR | Artifact Registry |
| Secrets | AWS Secrets Manager | Azure Key Vault | Google Secret Manager |
| Networking | VPC/CNI | VNet/CNI | VPC/CNI |

## 21. SRE readiness checklist

- [ ] Source and destination model documented.
- [ ] AppProject reviewed for least privilege.
- [ ] Four Applications target separate namespaces in one cluster.
- [ ] Chart-local values paths validated.
- [ ] Image digest pinning enforced.
- [ ] All environment overlays render offline.
- [ ] Dev Application manually synced in approved lab.
- [ ] Sync, health and application SLIs recorded separately.
- [ ] Multi-source reference behavior understood.
- [ ] Resource ownership collisions prevented.
- [ ] Prune, deletion and PVC retention risks reviewed.
- [ ] Three failure scenarios tested or documented as not tested.
- [ ] GitOps rollback runbook validated.

## 22. Evidence worksheet

\`\`\`text
CHAPTER 041 — ARGO CD APPLICATION ARCHITECTURE
Date:
Operator/reviewer:
Cluster/context:
GitLab GitOps repository:
Resolved Git commit:
Chart version and package digest:
Verified image digest:
AppProject:
Allowed source repositories:
Allowed destinations:
Application names:
Namespace mapping:
Values files:
Offline render results:
Dev sync/health:
Deployment readiness:
HTTP error/latency baseline:
Ownership review:
Multi-source compatibility:
Failure tests:
Git revert recovery:
Open risks:
Decision: PASS / NOT READY / NOT TESTED
\`\`\`

## 23. Knowledge checks

1. How does an Application differ from an AppProject?
2. Why do four namespaces not mean four clusters?
3. How does \`targetRevision\` differ between Git and a Helm chart repository?
4. Why must chart-local Helm values paths be validated?
5. When are multiple sources appropriate?
6. What does \`ref: values\` mean in a multi-source Application?
7. What happens when two Applications own the same Kubernetes object?
8. Why can an Application be Synced but Degraded?
9. Why is Git revert preferred to independent Helm rollback?
10. Which evidence proves a promotion is safe?

## 24. Completion

**Pass:** You can design four namespace-specific Applications, validate their Git/Helm sources and destinations, enforce AppProject restrictions, detect ownership collisions and recover safely through GitOps.

**Next: Chapter 042 — Argo CD ApplicationSets, Generators, Templates and Automated Application Provisioning.**
