# Chapter 042 — Argo CD ApplicationSets, Generators, Templates and Automated Application Provisioning

**Part 09 — Argo CD Applications and ApplicationSets** | **Chapter 042 of 100**  
**Audience:** SRE, platform infrastructure and Kubernetes administrators  
**Prerequisites:** Chapters 036–041, a working Argo CD installation, an approved GitOps repository and Helm chart  
**Reference design:** One Kubernetes cluster, Argo CD in \`argocd\`, workloads in \`demo-dev\`, \`demo-test\`, \`demo-staging\`, \`demo-prod\`.

> **Safety:** ApplicationSets create and update Application resources automatically. A template or generator change can affect many environments at once. First inspect generator output, use a disposable lab, keep Application sync manual, disable pruning and self-heal, and do not delete a production ApplicationSet without understanding Application ownership and deletion policy. Never put credentials in generator templates or Git.

## 1. Learning objectives

By completing this chapter you will:

1. Explain the ApplicationSet controller and its relationship to Application reconciliation.
2. Choose List, Git, Cluster and Matrix/Merge generators appropriately.
3. Design a deterministic template that creates four Applications in one cluster.
4. Separate environment metadata, Helm values and promotion policy.
5. Validate generated Applications and avoid naming/destination collisions.
6. Understand requeue intervals, Git polling/webhooks and generator refresh.
7. Control ApplicationSet modification and generated Application permissions.
8. Troubleshoot generator errors, template rendering and reconciliation.
9. Recover from bad generator changes through GitOps.
10. Produce an operational acceptance record with safety evidence.

## 2. Architecture and ownership

\`\`\`text
GitLab CI: build/test/scan/sign ONCE
             |
    image@sha256:<digest>
             |
      Reviewed GitOps repo
             |
   ApplicationSet definition
             |
   ApplicationSet controller
      generator + template
             |
       FOUR Applications
          |   |   |   |
       dev test stage prod
             |
    Argo CD application controller
             |
      Kubernetes API
             |
         ONE cluster
\`\`\`

**ApplicationSet controller:** Generates and maintains \`Application\` objects. **Application controller:** Compares each Application's rendered desired manifests with Kubernetes and performs authorized sync. ApplicationSet itself does not deploy Pods.

An AppProject constrains allowed source repositories and destination namespaces; Kubernetes RBAC and admission policies must independently constrain controller permissions.

## 3. When to use ApplicationSets

Use ApplicationSets when a platform manages many similarly structured Applications across environments, clusters, tenants or repositories. For four fixed namespaces, a List generator is an understandable starting point. ApplicationSets are not mandatory: four explicitly reviewed Application manifests may be simpler when production requires different ownership or approval gates.

| Method | Best use | Operational risk |
| --- | --- | --- |
| Explicit Applications | Few Apps, highly individualized policy | Repetitive configuration |
| List generator | Fixed approved environment inventory | Wrong list entry impacts destination |
| Git directory/file generator | App inventory in Git | Untrusted Git changes can create Apps |
| Cluster generator | Fleet inventory based on registered clusters | Label/credential drift, unintended targets |
| Matrix generator | Cartesian product of generator outputs | Unexpected multiplication of Applications |
| Merge generator | Combine generator parameter sets | Override precedence and missing keys |

Choose the least complex generator that meets governance requirements.

## 4. Generator mechanics

ApplicationSet evaluation follows:

1. Read generator configuration and discover parameter sets.
2. Render an Application template once for each parameter set.
3. Create/update/delete generated Applications according to ApplicationSet reconciliation and policy.
4. Let the Application controller compare/sync those Applications separately.

**Important:** Generated Application deletion is not equivalent to workload pruning. Depending on finalizers, ownership and policy, removing an Application may cascade to managed resources. Test deletion behavior in a disposable environment before adopting it.

## 5. Reference GitOps repository layout

\`\`\`text
demo-gitops/
├── charts/demo-app/
│   ├── Chart.yaml
│   ├── Chart.lock
│   ├── values.yaml
│   ├── values.schema.json
│   ├── env/
│   │   ├── dev-values.yaml
│   │   ├── test-values.yaml
│   │   ├── staging-values.yaml
│   │   └── prod-values.yaml
│   └── templates/
├── argocd/
│   ├── projects/demo-platform.yaml
│   ├── applicationsets/demo-environments.yaml
│   └── applications/  # prior explicit manifests; do not apply concurrently
└── docs/
    ├── promotion-policy.md
    ├── generator-change-runbook.md
    └── evidence.md
\`\`\`

**Migration rule:** Never let an explicit Application and an ApplicationSet fight for ownership of the same Application. Review existing resources, plan adoption and rollback, and migrate only with approval.

## 6. Lab A — Preflight (read-only)

\`\`\`bash
kubectl config current-context
kubectl get crd applicationsets.argoproj.io
kubectl get pods,deployments -n argocd
kubectl get appprojects.argoproj.io -n argocd
kubectl get applications.argoproj.io -n argocd
kubectl get applicationsets.argoproj.io -n argocd
\`\`\`

Inspect the ApplicationSet controller's Deployment, logs, Kubernetes ServiceAccount and ClusterRoleBindings. Confirm that Argo CD is installed at an approved version supporting the chosen generator and template features.

**Windows PowerShell:** These \`kubectl\` commands run unchanged. Use \`Select-String\` rather than \`grep\` when filtering.

## 7. Lab B — First List generator

\`argocd/applicationsets/demo-environments.yaml\`:

\`\`\`yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: demo-environments
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - name: dev
            namespace: demo-dev
            valuesFile: dev-values.yaml
          - name: test
            namespace: demo-test
            valuesFile: test-values.yaml
          - name: staging
            namespace: demo-staging
            valuesFile: staging-values.yaml
          - name: prod
            namespace: demo-prod
            valuesFile: prod-values.yaml
  template:
    metadata:
      name: 'demo-app-{{name}}'
    spec:
      project: demo-platform
      source:
        repoURL: https://gitlab.example.com/platform/demo-gitops.git
        targetRevision: main
        path: charts/demo-app
        helm:
          releaseName: demo-app
          valueFiles:
            - 'env/{{valuesFile}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{namespace}}'
      syncPolicy:
        syncOptions:
          - CreateNamespace=false
  syncPolicy:
    applicationsSync: create-update
\`\`\`

This example uses the standard fasttemplate parameter syntax (\`{{name}}\`), not \`goTemplate: true\`. The ApplicationSet \`applicationsSync: create-update\` limits the controller from deleting generated Applications during routine reconciliation, but it **does not by itself guarantee workload retention** if the ApplicationSet is deleted or garbage collection/finalizers apply. The generated Applications do not have automated sync enabled.

**Critical:** The example requires the \`demo-platform\` AppProject and the chart-local values files to exist. Use real approved GitLab URLs in your lab.

## 8. Understand the generated output

The List generator yields:

| Generator \`name\` | Generated Application | Destination | Helm values |
| --- | --- | --- | --- |
| dev | \`demo-app-dev\` | \`demo-dev\` | \`env/dev-values.yaml\` |
| test | \`demo-app-test\` | \`demo-test\` | \`env/test-values.yaml\` |
| staging | \`demo-app-staging\` | \`demo-staging\` | \`env/staging-values.yaml\` |
| prod | \`demo-app-prod\` | \`demo-prod\` | \`env/prod-values.yaml\` |

All four Applications target **the same Kubernetes cluster** via \`https://kubernetes.default.svc\`. They are not four clusters or four Argo CD installations.

## 9. Lab C — Validate manifests and rendered chart

\`\`\`bash
kubectl apply --dry-run=client -f argocd/applicationsets/demo-environments.yaml
kubectl apply --dry-run=server -f argocd/applicationsets/demo-environments.yaml
helm dependency build charts/demo-app
helm lint charts/demo-app
\`\`\`

Then render each environment offline:

\`\`\`bash
helm template demo-app charts/demo-app --namespace demo-dev \
  -f charts/demo-app/env/dev-values.yaml > rendered-dev.yaml
helm template demo-app charts/demo-app --namespace demo-test \
  -f charts/demo-app/env/test-values.yaml > rendered-test.yaml
helm template demo-app charts/demo-app --namespace demo-staging \
  -f charts/demo-app/env/staging-values.yaml > rendered-staging.yaml
helm template demo-app charts/demo-app --namespace demo-prod \
  -f charts/demo-app/env/prod-values.yaml > rendered-prod.yaml
\`\`\`

Dry-run validates the ApplicationSet resource schema/admission but **does not prove** generator output, GitLab credentials or Application runtime health. Inspect generated Applications after applying in an authorized lab.

## 10. Lab D — Apply and inspect generation (disposable only)

Before applying, verify no conflicting Applications are already managed manually:

\`\`\`bash
kubectl get applications.argoproj.io -n argocd
kubectl get applicationsets.argoproj.io -n argocd
\`\`\`

After approval:

\`\`\`bash
kubectl apply -f argocd/applicationsets/demo-environments.yaml
kubectl get applicationset demo-environments -n argocd -o yaml
kubectl get applications.argoproj.io -n argocd
kubectl describe applicationset demo-environments -n argocd
\`\`\`

Expected generated Application names are \`demo-app-dev\`, \`demo-app-test\`, \`demo-app-staging\`, and \`demo-app-prod\`. They should be manual-sync, and therefore may be \`OutOfSync\` before first deployment.

Check ownership references to confirm the Applications are generated by the intended ApplicationSet.

## 11. Lab E — Review and sync Dev only

\`\`\`bash
argocd app get demo-app-dev
argocd app diff demo-app-dev
\`\`\`

After reviewing the diff and obtaining approval:

\`\`\`bash
argocd app sync demo-app-dev
argocd app wait demo-app-dev --sync --health --timeout 300
kubectl get deployment,pods,svc -n demo-dev
kubectl get endpointslices -n demo-dev
\`\`\`

Do not sync Test, Staging or Production merely because the ApplicationSet created their Application objects. GitLab promotion gates still apply.

## 12. Git directory generator

For applications discovered from approved directories:

\`\`\`yaml
generators:
  - git:
      repoURL: https://gitlab.example.com/platform/demo-gitops.git
      revision: main
      directories:
        - path: apps/*
\`\`\`

This can discover application directories automatically. **Security:** A Git change adding a directory could create a new Application. Restrict who can modify generator configuration and discovered paths. Validate generated names, destinations and Project constraints.

Use a deterministic naming convention; avoid directory names that could produce invalid Kubernetes resource names.

## 13. Git file generator

For metadata-driven environment provisioning:

\`\`\`yaml
generators:
  - git:
      repoURL: https://gitlab.example.com/platform/demo-gitops.git
      revision: main
      files:
        - path: environments/*.json
\`\`\`

Each matching JSON file can supply parameters. Define a schema and CI validation for \`name\`, \`namespace\`, \`chartPath\`, \`valuesFile\`, \`sourceRevision\` and allowed destination. A malformed or unauthorized environment record must fail validation before merge.

**Governance:** Do not let arbitrary Git file contents choose privileged AppProjects, cluster API servers or sensitive namespaces.

## 14. Cluster generator

The Cluster generator discovers Argo CD-registered clusters, often filtered by labels. This is useful for EKS, AKS and GKE fleet operations but is **not needed** for the four-namespace single-cluster reference lab.

Illustrative pattern:

\`\`\`yaml
generators:
  - clusters:
      selector:
        matchLabels:
          platform.example.com/gitops-enabled: "true"
\`\`\`

A label change or cluster registration change can affect many generated Applications. Protect cluster Secrets, labels and generator configuration. The local cluster may not appear in label-selected results unless it is explicitly represented by a cluster Secret; verify the installed version's behavior.

## 15. Matrix and Merge generators

**Matrix** combines parameter sets across generators. For example, three apps × four environments can create twelve Applications. Before rollout, calculate the expected count and verify that no combination targets a prohibited namespace.

**Merge** combines parameter sets using merge keys and precedence. Use it to overlay environment or cluster-specific metadata, but document override behavior and reject missing/duplicate keys.

Prefer a simple List generator until the number of Applications and governance requirements justify more complex composition.

## 16. Go templates and missing keys

Newer ApplicationSet designs can use Go templates:

\`\`\`yaml
spec:
  goTemplate: true
  goTemplateOptions:
    - missingkey=error
\`\`\`

With Go templating, expression syntax changes (for example, \`{{.name}}\` rather than \`{{name}}\`). Do not mix the two styles in the same manifest. Test rendering with the actual Argo CD version, especially for nested generator parameters and optional keys.

## 17. Generator refresh and reconciliation

Generator outputs can change because of:

- Git commits adding/removing environment records.
- Repository polling or webhook refresh.
- Cluster Secret registration or label changes.
- ApplicationSet template updates.
- Controller restart or cache refresh.

Reconciliation is eventually consistent; do not promise an exact propagation time without measuring the deployed release and configuration. Monitor ApplicationSet controller errors, generated Application counts and reconciliation latency.

## 18. Security and policy boundaries

ApplicationSets introduce an additional trust boundary: the generator/template can create Applications, and Applications can deploy Kubernetes resources.

Protect:

1. GitLab protected branches and CODEOWNERS for ApplicationSet definitions.
2. Argo CD RBAC for ApplicationSet create/update/delete.
3. AppProject source, destination and resource restrictions.
4. Controller Kubernetes RBAC.
5. Cluster registration credentials and labels.
6. Repository credentials and external secrets.
7. Application naming and resource ownership.
8. Deletion, pruning and finalizer behavior.

Avoid granting developers arbitrary control over \`spec.template.spec.project\` or \`destination.server\`. Validate the selected Argo CD version's ApplicationSet security guidance before delegating generator changes.

## 19. Drift and ownership collisions

An ApplicationSet manages Application objects. The Application controller manages Kubernetes resources described by those Applications.

Collision scenarios:

- An explicit Application and an ApplicationSet both manage the same Application.
- Two generated Applications render the same Kubernetes resource.
- A generator rename changes an Application name, leaving the old Application subject to deletion/retention policy.
- Two chart releases use identical names in the same namespace.
- A Project restriction is loosened unintentionally.

Before adoption, inspect \`ownerReferences\`, generated names, target namespaces and rendered resource identities. Consider \`FailOnSharedResource=true\` as a defense-in-depth sync option where supported, but test it before production.

## 20. Failure injection lab

Perform in an approved disposable scope:

| Test | Fault | Expected observation | Recovery |
| --- | --- | --- | --- |
| 1 | Missing List generator parameter | Template/render error or invalid Application | Restore required key |
| 2 | Duplicate generated Application name | Collision/conflict | Enforce unique naming |
| 3 | Wrong values file | Application manifest-generation error | Correct chart-local file |
| 4 | Unauthorized destination | AppProject blocks Application sync | Restore allowed namespace |
| 5 | Invalid Git revision | Source comparison error | Restore reviewed revision |
| 6 | Unapproved extra environment | Unexpected generated Application | Reject MR and revert |
| 7 | Deleted generator entry | Potential Application removal/retention | Stop; review deletion policy |
| 8 | Controller unavailable (tabletop) | Generation delayed | Restore controller and validate backlog |

Do not simulate deletion by removing a production generator entry. Tabletop exercises count only as simulations, not live recovery validation.

## 21. Incident runbook — Unexpected Applications generated

**Scenario:** A merged generator change unexpectedly creates an Application targeting an unauthorized namespace.

1. Confirm cluster context, ApplicationSet name, Git commit and change owner.
2. Stop any unauthorized synchronization; assess whether generated Applications have auto-sync enabled.
3. Inspect generator inputs, template and expected Application count.
4. Verify AppProject and Kubernetes RBAC denied unauthorized destinations.
5. Capture controller events and sanitized logs.
6. Revert the offending GitOps commit through an approved MR.
7. Review ApplicationSet deletion policy, owner references and finalizers **before** removing any Application.
8. Reconcile and confirm the expected Application inventory.
9. Verify workloads and SLOs remain healthy.
10. Document root cause, blast radius, recovery and preventive CI policy.

Never blindly delete an ApplicationSet to fix unexpected generation.

## 22. SRE operational observability

| Signal | Purpose |
| --- | --- |
| ApplicationSet controller availability | Generation control plane health |
| Generator evaluation errors | Invalid Git/cluster metadata |
| Expected vs actual Application count | Missing or unexpected targets |
| Reconciliation duration | Controller backlog |
| Generated Application OutOfSync | Pending or failed deployment |
| Generated Application Degraded | Runtime problems |
| AppProject destination denial | Policy enforcement |
| Unexpected Application deletion | Destructive change detection |
| GitLab MR and audit events | Traceability |
| HTTP error rate/p95/p99 | User-facing SLO impact |

Define alerts based on measured baselines and distinguish intentional manual-sync waiting from incidents.

## 23. EKS, AKS and GKE considerations

ApplicationSet templates can target EKS, AKS and GKE clusters when those clusters are securely registered with Argo CD. The same generator pattern applies, but cloud workload identity, private API endpoints, DNS, registry authentication and RBAC differ.

This chapter **does not** provision multiple clusters. The lab deliberately targets one cluster and four namespaces; fleet patterns appear in later chapters.

## 24. Acceptance checklist

- [ ] ApplicationSet controller and CRD verified.
- [ ] Existing Application ownership reviewed.
- [ ] List generator creates exactly four expected Application definitions.
- [ ] All four targets belong to the same approved cluster.
- [ ] Source repository and chart-local values paths validated.
- [ ] Generated Applications use manual sync, no prune/self-heal.
- [ ] AppProject limits sources/destinations.
- [ ] Dev diff reviewed and sync tested only with authorization.
- [ ] Git/Cluster/Matrix/Merge generator risks understood.
- [ ] Template style and missing-key handling documented.
- [ ] Deletion policy and finalizers reviewed.
- [ ] At least three failure scenarios tested or marked not tested.
- [ ] Incident recovery and monitoring evidence captured.

## 25. Evidence worksheet

\`\`\`text
CHAPTER 042 — APPLICATIONSETS
Date:
Operator/reviewer:
Cluster/context:
Argo CD version:
ApplicationSet controller status:
GitLab repository:
Source commit:
Generator type:
Template mode (fasttemplate / Go):
Expected Application count:
Actual Application count:
Generated names:
Destination namespaces:
AppProject:
Helm chart version:
Verified image digest:
Manual sync policy:
Dev sync/health:
Controller reconciliation metrics:
Ownership/finalizer review:
Failure tests:
Recovery Git commit:
SLO evidence:
Open risks:
Decision: PASS / NOT READY / NOT TESTED
\`\`\`

## 26. Knowledge checks

1. What does the ApplicationSet controller do that the Application controller does not?
2. Why is a List generator suitable for four fixed environments?
3. How can a Git directory generator create unexpected Applications?
4. Why might a Cluster generator omit the local cluster?
5. What is the risk of a Matrix generator?
6. What changes when \`goTemplate: true\` is enabled?
7. Why does \`applicationsSync: create-update\` not guarantee workload retention after ApplicationSet deletion?
8. How do AppProjects limit generator-created Applications?
9. What is the danger of duplicate Application names or resource ownership?
10. How should an SRE recover from a bad generator change?

## 27. Completion

**Pass:** You can safely generate four manual-sync Applications from a List generator, validate source/destination policy, inspect generated ownership, and recover from generator failures through reviewed GitOps changes.

**Next: Chapter 043 — Argo CD ApplicationSet Git and Cluster Generators for Multi-Environment Operations.**
