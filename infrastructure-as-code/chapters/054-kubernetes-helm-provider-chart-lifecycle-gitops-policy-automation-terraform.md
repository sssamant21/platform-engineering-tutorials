# Chapter 054 — Kubernetes Helm Provider, Chart Lifecycle, GitOps Integration and Policy Automation with Terraform

**Part 11 — Kubernetes and Helm | Chapter 054 of 120**  
**Audience:** SRE, DBRE, platform, DevSecOps and GitOps engineers.  
**Prerequisites:** Chapters 051–053, Terraform >=1.7, Python >=3.9; an explicitly approved disposable cluster for optional integration.

> **Safety and evidence:** Required labs create only local \`terraform_data\` contracts. No cluster, Helm release or secret is created by the mandatory exercises. Provider examples are review-only and deliberately not runnable as production deployments. Python policy tests evaluate declared evidence and a simplified plan fixture, not native Terraform plans, real admission policy or Kubernetes enforcement. Never uninstall stateful Helm releases or delete CRDs/PVCs without explicit DBRE approval.

## 1. Learning objectives

Explain Helm architecture and release state, configure Terraform's Helm provider securely, pin chart and image versions, separate CRD/bootstrap from custom resources, review chart values and hooks, integrate Argo CD/Flux without dual ownership, automate fail-closed policies in CI, manage safe upgrades and rollbacks, and run production SRE/DBRE incident and disaster-recovery drills.

## 2. Production architecture

~~~text
 Git PR -> CI: fmt / validate / chart lint / render / policy / approval
                    |
              OIDC short-lived identity
                    |
            Terraform platform root
              /                \
        Helm provider      Kubernetes provider
              |                |
        pinned charts     tenant guardrails
        ingress/metrics   namespaces/RBAC/PSA
              |
        CRDs -> readiness gate -> CRs in separate stage
              |
        Argo CD / Flux owns application delivery (not Terraform)
              |
       Deployment / StatefulSet / Service / PDB
              |
     CSI volumes + database backup + observability
              |
       incident response + DR acceptance
~~~

Use three explicit ownership tiers: cloud cluster bootstrap, Terraform-owned platform add-ons, and GitOps-owned application workloads. Helm is a package manager; Argo CD/Flux can deploy Helm charts, but Terraform and GitOps must not reconcile the same release or rendered objects simultaneously.

## 3. Helm fundamentals and provider lifecycle

A chart contains templates, values, metadata and dependencies. Helm renders Kubernetes manifests and stores release history in the target cluster (commonly Secrets). A Terraform \`helm_release\` tracks the desired chart version, repository, namespace and values through Terraform state. Review Terraform Helm provider major-version differences before copying syntax; the example in this chapter is explicitly for provider v2 and is not a v3 compatibility claim.

Lifecycle:
1. Authenticate with explicit kubeconfig context or approved workload identity.
2. Pin chart repository, chart version, provider version and image digest.
3. Inspect dependencies, rendered manifests, RBAC, admission hooks and CRDs.
4. Create namespace and baseline RBAC/network policy in a separate stage.
5. Install CRDs before any custom resource plan requiring schema discovery.
6. Plan, review and apply the Helm release.
7. Verify rollout, endpoints, health probes, PDB, telemetry and SLO.
8. Upgrade through canary/staging, document rollback and database schema compatibility.

**Important semantics:** \`atomic\`, \`wait\`, \`timeout\`, \`cleanup_on_fail\` and \`recreate_pods\` behavior is provider/chart-version-specific. A Helm rollback does not roll back database migrations, external API contracts or data loss. Hooks may perform destructive operations and must be reviewed before deployment.

## 4. Chart security and provenance

Pin exact chart versions, prefer trusted repositories/OCI registries, verify chart provenance/signatures when supported and pin container images by immutable digest. Review \`helm template\` output for wildcard ClusterRoleBindings, privileged pods, host networking, hostPath, unbounded resources, permissive network policies, external service exposure and unexpected admission webhooks.

Treat \`values.yaml\` as potentially sensitive. Terraform sensitive outputs do not guarantee secrets are absent from state. **Do not inject passwords or TLS private keys via Terraform Helm values**; use approved workload identity and secret delivery mechanisms with an auditable boundary. Protect release metadata, Terraform remote state and Kubernetes audit logs.

## 5. CRDs, operators and safe dependencies

Kubernetes providers may discover CRD schemas during planning. Creating a CRD and a dependent \`kubernetes_manifest\` custom resource in the same initial plan may fail because the schema does not exist yet. Use separate CI stages with readiness checks and version compatibility tests. Helm CRDs can have special upgrade/deletion behavior; chart uninstall is not equivalent to safe CRD lifecycle management.

For database operators (PostgreSQL, MongoDB, Kafka, Elasticsearch), coordinate CRD changes with operator compatibility, quorum, persistent volume topology, backup/PITR, restore validation and DBRE-approved maintenance. Avoid Helm uninstall as a troubleshooting shortcut.

## 6. GitOps ownership and drift

| Object | Preferred owner | Drift control |
|---|---|---|
| Cluster and node pools | Cloud Terraform root | Terraform plan |
| Shared ingress/CSI/monitoring chart | Platform Terraform or GitOps (choose one) | owner registry |
| Namespace policy and quota | Platform Terraform | policy gate + audit |
| Application Helm chart | Argo CD/Flux | Git reconciliation |
| Database operator CRDs | Dedicated platform stage | compatibility/backup gate |
| Application replicas | HPA where enabled | exclude competing field ownership |

Terraform's desired state, Helm release history, admission mutation and GitOps reconciliation can produce perpetual drift. Document the source of truth at resource/field level; import existing resources only after ownership handoff. Never broadly ignore security-related changes to silence plans.

## 7. Policy-as-code and CI/CD

The minimum pipeline checks Terraform formatting/validation, chart metadata and render output, security policy, least-privilege RBAC, image provenance, secret exposure, state isolation, deletion/replacement, required approvals and rollout evidence. Use fail-closed behavior for missing policy configuration or malformed input. Native Terraform plan JSON requires a tested parser, including \`resource_changes\`, \`change.actions\`, unknown values and provider-specific paths; the offline gate in this lab intentionally accepts a **simplified fixture**.

Recommended staged delivery:
- PR: static analysis, chart lint/render, OPA/Conftest or equivalent, Python negative tests.
- Pre-apply: explicit context, identity, release inventory, reviewed plan and signed change.
- Staging: canary, rollback and CRD compatibility tests.
- Production: SLO-aware deployment, observability, change freeze and DBRE approval for stateful workloads.
- Post-apply: verify effective RBAC, actual admission, pod health, release status, backups and cost.

## 8. Hands-on labs

Directory: \`infrastructure-as-code/labs/chapter-054/\`.

### Lab A — Offline Terraform contracts

~~~bash
cd infrastructure-as-code/labs/chapter-054
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=dev.tfplan
terraform apply dev.tfplan
terraform output -json
terraform state list
terraform destroy -var-file=environments/dev.tfvars
~~~

Four \`terraform_data\` contracts represent chart supply chain, Helm release safety, GitOps ownership and operational approval. Production preconditions reject unpinned charts, unknown hooks, broad RBAC, secret payloads in Terraform state, competing reconcilers, unapproved CRD deletion and absent recovery evidence. **No Kubernetes changes occur.**

### Lab B — Fail-closed Python policy

~~~bash
python3 helm_gate.py fixtures/helm-safe.json fixtures/plan-safe.json helm-policy.json
python3 helm_gate.py fixtures/helm-unsafe.json fixtures/plan-destructive.json helm-policy.json
python3 -m unittest -v test_helm_gate.py
bash run-preflight.sh
~~~

The safe fixture should pass; unsafe and destructive fixtures must fail. Unit tests cover individual control failures, malformed plans, unapproved resource types and fail-open policy tampering. This is a declared-evidence test, not a Helm release security attestation.

### Lab C — Optional Helm sandbox

1. Confirm an approved disposable Kubernetes context, namespace, service identity, provider version and chart provenance.
2. Inspect \`examples/helm-platform.tf.example\` and \`examples/helm-readonly-diagnostics.sh.example\`; keep the example separate from the offline root.
3. Select a verified non-stateful chart and exact version; render and lint offline, inspect RBAC, hooks, images and network exposure.
4. Install under a narrowly scoped identity, inspect \`helm history\`, Deployment health and PDB; perform a compatible version upgrade.
5. Simulate failed readiness, verify Helm/Terraform behavior and roll back; document evidence and drift.
6. Separately stage a CRD and compatible custom resource in an approved sandbox; validate schema readiness.
7. Test GitOps handoff by disabling one owner before enabling the other. Do not run two active reconcilers for the same release.
8. Record actual rollback time, service availability and any database compatibility requirements.

### Lab D — Stateful upgrade and DR tabletop

Review a database operator Helm upgrade, CSI snapshot/PITR, WAL consistency, RPO/RTO, CRD migration and PVC reclaim policy. Inject a broken hook, stuck release and wrong chart values. Deny uninstall and CRD/PVC deletion; restore from isolated validated backup where required.

## 9. Production SRE/DBRE incident matrix

| Incident | Signal | Triage | Safe recovery |
|---|---|---|---|
| Helm pending-upgrade | blocked release | \`helm status/history\`, hooks, events | controlled release recovery |
| Hook Job timeout | failed upgrade | Job logs, RBAC, DNS | fix hook, rerun reviewed release |
| CRD schema mismatch | no matches for kind | CRD served versions | stage compatible CRD |
| Chart image pull failure | ImagePullBackOff | registry auth, digest, network | fix pull identity/digest |
| Privileged chart rejected | admission denied | PSA, webhook | correct chart security |
| Terraform/GitOps oscillation | repeated drift | owner/managed fields | pause and transfer ownership |
| Secrets leaked to state | security finding | values, state access | revoke/rotate, migrate delivery |
| Helm uninstall removes workload | unexpected deletion | release ownership, PVC policy | restore from backup and Git |
| DB schema incompatible with rollback | 5xx/SQL errors | migration compatibility | DBRE-controlled forward fix |
| Operator CRD upgrade breaks database | quorum/health loss | operator logs, backups | freeze writes, restore safely |
| HPA drives DB pool exhaustion | connection errors | replicas × pool | cap fan-out, backpressure |
| Cross-cluster kubeconfig | wrong target | context, audit | freeze changes and contain |

## 10. Troubleshooting commands

~~~bash
kubectl config current-context
kubectl get pods,deploy,sts,job,pdb -A
kubectl get events -A --sort-by=.lastTimestamp
kubectl get crd
kubectl get pvc,pv,storageclass
kubectl auth can-i get deployments -n NAMESPACE
helm list -A
helm status RELEASE -n NAMESPACE
helm history RELEASE -n NAMESPACE
helm get manifest RELEASE -n NAMESPACE
helm lint ./CHART
helm template RELEASE ./CHART -n NAMESPACE
terraform providers
terraform state list
terraform plan -var-file=environments/dev.tfvars
~~~

Do not print release values containing secrets, access tokens or sensitive Terraform state to incident tickets.

## 11. Production runbooks

**Pre-change:** verify target cluster, chart/provider pinning, OCI provenance, hook/CRD review, RBAC, network policy, PDB, backups, owner registry, plan, rollback compatibility, ticket and Security/DBRE approval.

**Failed upgrade:** freeze competing reconcilers, inspect release history and hook events, restore a compatible chart version, validate SLO and data migrations; avoid blind uninstall.

**GitOps drift:** identify Terraform vs Argo CD/Flux owner, pause one under change approval, reconcile release/state, document handoff and resume only the chosen owner.

**CRD incident:** stop dependent applies, inspect served/storage versions, coordinate operator and database owners, stage migration, validate custom resources and data integrity.

**Secret exposure:** revoke credentials, audit state and release metadata access, rotate secrets, migrate to workload identity/secret operator, validate consumers.

**Stateful DR:** preserve PV/PVC, freeze unsafe writes, restore isolated consistent database backup, validate transactions, cut over under DBRE approval and measure actual RPO/RTO.

## 12. 100-point acceptance

| Area | Points | Required evidence |
|---|---:|---|
| Helm provider, chart provenance and lifecycle | 20 | version pins, chart review |
| CRD/operator, workload and DBRE safety | 20 | staged schema and restore |
| GitOps ownership and drift control | 20 | owner registry and handoff |
| Terraform contracts and negative policy tests | 15 | executed CI logs |
| Production incidents, rollback and DR | 15 | incident timeline, RPO/RTO |
| Security, audit, SLOs and FinOps | 10 | sign-offs and monitoring |
| **Total** | **100** | |

**Pass >=85/100 and zero critical findings:** no leaked secrets, wildcard admin grants, unapproved Helm uninstall, CRD/PVC destruction, dual ownership or unverified database restore. Authored examples are not live acceptance evidence.

## 13. Review and next

Why does Helm rollback not revert SQL migrations? Why should CRDs be staged? How can Terraform and GitOps fight over a release? Which Helm values can leak into state? What constitutes proof of a successful database recovery?

**Next proposed:** Chapter 055 — Kubernetes and Helm Production Platform Engineering, Reliability and GitOps Capstone.
