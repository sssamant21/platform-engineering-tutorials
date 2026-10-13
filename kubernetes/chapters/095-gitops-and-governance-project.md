# Chapter 095 — GitOps and Governance Project

**Track:** Kubernetes Administration · **Part 19 — GitOps and Platform Automation (Final Capstone)**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** Platform engineers, Kubernetes administrators, SREs, security engineers, FinOps practitioners  
**Prerequisites:** Chapters 091–094; kubectl, Helm, Git, PowerShell; disposable staging cluster; Argo CD **or** Flux; Kyverno **or** Gatekeeper; a CNI that enforces NetworkPolicy; Prometheus-compatible monitoring and access to cost reports.

## Project objective

Build a reproducible, policy-governed, multi-tenant Kubernetes platform that reconciles approved Git changes, blocks unauthorized deployments, constrains resource consumption, measures tenant costs and supports a rehearsed incident rollback. This project combines GitOps, admission control, namespace governance and FinOps into a single acceptance exercise.

**Success means:** authorized changes converge; unauthorized or unsafe changes fail with evidence; tenant boundaries hold; cost attribution is explainable; SLOs remain within thresholds; rollback works without creating an uncontrolled security exception.

## 1. Architecture and trust boundaries

```text
Developer PR → protected Git branch → CI validation → approval
                                           |
                                           v
                           Argo CD or Flux reconciler
                                           |
                                           v
Kubernetes API → authentication → RBAC → admission policy → persisted object
                                           |
                      +--------------------+-------------------+
                      |                    |                   |
                 Tenant Alpha         Tenant Beta       Shared Platform
                 namespace            namespace         controllers
                      |                    |
                 quota + PSA          quota + PSA
                 netpol + SA          netpol + SA
                      +--------------------+
                                           |
                             metrics + billing exports
                                           |
                                cost allocation/report
```

Namespace separation is a logical boundary, not equivalent to dedicated clusters. Cluster-scoped resources, node kernels, storage, cloud IAM, network infrastructure and GitOps controllers remain shared trust surfaces.

## 2. Safety rules and project scope

- Perform destructive or deny-all policy experiments **only in a disposable staging cluster**.
- Record `kubectl config current-context` before every apply, rollback and cleanup.
- Keep platform controllers, CNI, DNS and admission webhooks outside tenant test namespaces.
- Do not give tenant users cluster-admin or unrestricted cluster-scoped GitOps permissions.
- Do not put cloud credentials, Git tokens, kubeconfigs or secrets in the repository.
- Do not uninstall admission controllers or delete shared namespaces during recovery.
- Use version-pinned, organization-approved controller charts/manifests; do not blindly install the latest release.
- Maintain an independent emergency access path, reviewed and audited.
- This document defines tests and expected results; it does **not** assert that any test was executed.

## 3. Deliverables and evidence

Create these project artifacts:
1. Git repository layout, branch protections and CODEOWNERS.
2. Namespace manifests and tenant ownership metadata.
3. Namespaced RBAC and workload identity mapping.
4. ResourceQuota, LimitRange and Pod Security Admission labels.
5. NetworkPolicy deny-by-default plus narrowly scoped allow rules.
6. Policy-as-code in audit and enforce modes, with negative tests.
7. GitOps reconciliation and drift-detection records.
8. Workload dashboards, alerts, SLO thresholds and billing attribution.
9. Incident simulation timeline, Git rollback and post-recovery validation.
10. Acceptance report with screenshots/log excerpts, reviewer, timestamps and unresolved risks.

## 4. Reference Git repository layout (Lab 01)

```text
platform-gitops/
  README.md
  CODEOWNERS
  apps/
    alpha/
      deployment.yaml
      service.yaml
      kustomization.yaml
    beta/
      deployment.yaml
      service.yaml
      kustomization.yaml
  tenants/
    alpha/
      namespace.yaml
      rbac.yaml
      quota.yaml
      limitrange.yaml
      networkpolicy.yaml
      serviceaccount.yaml
      kustomization.yaml
    beta/
      ...
  policies/
    admission/
      ...
  clusters/
    staging/
      ...
    production/
      ...
  tests/
    positive/
    negative/
  evidence/
    .gitkeep
```

Separate platform-admin and tenant-owned paths with CODEOWNERS. Configure required pull-request approvals, signed commits if required, CI validation, and protected deployment branches. Ensure GitOps source credentials are read-only where possible. Keep secrets externalized via approved secret management.

**Acceptance:** tenant pull requests cannot silently modify platform policy, GitOps credentials or another tenant's directory.

## 5. Establish a safe baseline (Lab 02)

```powershell
kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
kubectl get namespaces --show-labels
kubectl get pods -A
kubectl get networkpolicy -A
kubectl get resourcequota -A
kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations
```

Capture Kubernetes version, CNI, GitOps controller version, admission controller version, namespace owners, workload baseline, error rate, p95 latency and available capacity. Verify the test cluster is disposable before proceeding.

## 6. Bootstrap GitOps safely (Lab 03)

Choose **one** reconciler for the capstone: Argo CD or Flux. Install with a version-pinned approved chart/manifest following Chapter 091. Grant the reconciler only the scope it needs, then point it to the staging directory. Do not let unreviewed tenant Git paths create arbitrary ClusterRoles or webhook configurations.

For Argo CD:

```powershell
kubectl get applications.argoproj.io -A
kubectl get appprojects.argoproj.io -A
kubectl get pods -n argocd
```

For Flux:

```powershell
kubectl get gitrepositories.source.toolkit.fluxcd.io -A
kubectl get kustomizations.kustomize.toolkit.fluxcd.io -A
kubectl get pods -n flux-system
```

Some CRDs are absent until the selected tool is installed. Configure namespace restrictions and controller identities using the tool's supported version-specific security model. **Acceptance:** an approved Git change is reconciled; a manual drift change is detected and corrected according to the chosen reconciliation policy.

## 7. Create tenant boundaries (Lab 04)

Use `tenant-alpha` and `tenant-beta` namespaces with owner, environment and cost-center labels. Apply Chapter 093's narrow Role/RoleBinding, ServiceAccount, ResourceQuota and LimitRange manifests through GitOps.

```powershell
kubectl get namespaces -L platform.example.com/team,platform.example.com/cost-center
kubectl get role,rolebinding,serviceaccount -n tenant-alpha
kubectl get resourcequota,limitrange -n tenant-alpha
kubectl get role,rolebinding,serviceaccount -n tenant-beta
```

Test impersonated service-account access if the operator is authorized to impersonate:

```powershell
kubectl auth can-i create deployments -n tenant-alpha --as=system:serviceaccount:tenant-alpha:alpha-deployer
kubectl auth can-i create deployments -n tenant-beta --as=system:serviceaccount:tenant-alpha:alpha-deployer
kubectl auth can-i get secrets -n tenant-alpha --as=system:serviceaccount:tenant-alpha:alpha-deployer
```

Expected under the example Chapter 093 Role: yes, no, no. If results differ, inspect other RoleBindings/ClusterRoleBindings before claiming isolation.

## 8. Enforce baseline workload security (Lab 05)

Enable Pod Security Admission **warn** and **audit** for `restricted` on tenant namespaces. Validate workloads before changing `enforce` to `restricted`; pin the Pod Security profile version to the cluster minor version for predictable upgrades.

```powershell
kubectl label namespace tenant-alpha pod-security.kubernetes.io/warn=restricted --overwrite
kubectl label namespace tenant-alpha pod-security.kubernetes.io/audit=restricted --overwrite
kubectl get namespace tenant-alpha --show-labels
```

In the actual GitOps project, represent these labels in `namespace.yaml` so they are not reverted. Test that a workload with an approved non-root user, no privilege escalation, dropped capabilities and runtime-default seccomp can be admitted. Test that a deliberately privileged test Pod is warned/audited, then denied after reviewed enforcement. Do not use a global exemption to fix one workload.

## 9. Network isolation and allowed dependencies (Lab 06)

Apply default-deny ingress/egress to each tenant. Add explicit rules for same-tenant application flows, DNS and documented shared services. Verify that the CNI actually enforces policies.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: tenant-alpha
spec:
  podSelector: {}
  policyTypes: ["Ingress", "Egress"]
```

Validate **both** a positive and a negative connection:
- Approved alpha client → approved alpha service: success.
- Beta client → alpha service: blocked.
- Alpha client → approved DNS resolver: success.
- Alpha client → unapproved destination: blocked.

A timeout alone is not evidence of network-policy enforcement: also prove that the destination was healthy and reachable from an allowed source. NetworkPolicy does not universally cover node/host-network paths.

## 10. Policy as code: audit then enforce (Lab 07)

Choose Kyverno or Gatekeeper using Chapter 092. Implement at least:
- Required ownership and cost-center labels.
- Nonprivileged workload requirements.
- Approved image registry controls.
- Resource requests and limits.
- Narrow, documented exception handling.

First deploy in audit/report mode and collect findings. After fixing expected violations, switch to enforce in staging and submit positive and negative manifests. For GitOps, use a PR-based promotion with policy-test evidence and rollback instructions.

**Acceptance:** a compliant workload is admitted; a deliberately noncompliant workload is denied with a named policy and clear message. Admission-webhook availability and failure policy must be reviewed separately.

## 11. Deploy tenant workloads (Lab 08)

Deploy a small stateless HTTP application to each tenant, with a pinned approved image digest, requests/limits, readiness/liveness probes, non-root security context, ServiceAccount and required labels. Use one test-only client per tenant to validate traffic. Confirm Deployment rollout, endpoints and application health.

```powershell
kubectl get deployments,pods,svc -n tenant-alpha -o wide
kubectl get deployments,pods,svc -n tenant-beta -o wide
kubectl get events -n tenant-alpha --sort-by=.lastTimestamp
kubectl rollout status deployment/alpha-api -n tenant-alpha --timeout=180s
```

`alpha-api` is an example name: create the corresponding Deployment manifest in the lab repository before running the rollout command.

## 12. Resource budgets and scheduling (Lab 09)

Create tenant quotas and container LimitRanges. Use Chapter 094 to calculate a **documented** budget rather than copying example values to production.

```powershell
kubectl describe resourcequota -n tenant-alpha
kubectl describe limitrange -n tenant-alpha
kubectl top pods -n tenant-alpha --containers
kubectl describe nodes
```

Negative test: submit a Pod whose requests exceed the remaining quota and capture the expected admission rejection. Positive test: a correctly sized Pod schedules and runs. Record allocatable node capacity, DaemonSet overhead, topology constraints and capacity for node failure. A ResourceQuota limits API resource consumption; it is **not** a dollar-spend ceiling.

## 13. Cost allocation and guardrails (Lab 10)

Collect a baseline cost window from provider billing exports and reconcile any OpenCost/Kubecost estimates to the same period. Attribute tenant charges using documented CPU/memory request weights or another approved model; retain **idle/shared/unallocated** cost as a visible line item.

Report:
- Effective billed cost and currency.
- Node-hours and idle capacity.
- Tenant allocation and unallocated share.
- CPU/memory requests vs p95 observed usage.
- Storage, network, load balancer and observability spend.
- Forecast and budget variance.

Do not claim dollar savings merely because resource requests decrease. Confirm actual infrastructure/billing changes and that SLOs remain healthy.

## 14. Drift detection and change promotion (Lab 11)

In staging, change a safe workload field directly with `kubectl`. Observe GitOps drift detection and reconcile according to configured sync settings. Then make the same approved change in Git via a reviewed PR and verify it persists.

Record Git commit, controller reconciliation event, observed drift, time to converge and affected workload. If auto-sync is disabled, a manual sync may be required; do not assume all controllers automatically repair drift.

**Acceptance:** the Git repository is the intended source of truth and manual cluster edits do not become undocumented permanent state.

## 15. Security incident simulation (Lab 12)

In a disposable namespace, deliberately attempt one unauthorized action:
- Cross-tenant Deployment creation using alpha identity in beta namespace.
- Privileged Pod creation after restricted PSA enforcement.
- Workload with a disallowed registry or missing ownership label.

Capture API error, rejecting authorization/admission layer, policy name, time, identity and evidence. Remediate the manifest or permission boundary; do not weaken all tenant policies to allow the test.

## 16. Cost and capacity regression simulation (Lab 13)

In staging, submit an oversized request or intentionally increase replicas within a fixed, capped cluster. Observe ResourceQuota rejection, Pending Pods or scheduling pressure without enabling uncontrolled autoscaler spend.

Capture the offending Git revision, resource delta, alert, SLO effect and rollback. Revert through Git and confirm the reconciler restores the prior approved state. Check PDBs, quotas and cluster autoscaler settings if recovery stalls.

## 17. GitOps failure and recovery drill (Lab 14)

Simulate a **non-destructive** configuration failure: for example, change an application Service selector in staging so it no longer selects healthy Pods. Do not deliberately disable the cluster API, CNI, DNS or admission controllers.

Runbook:
1. Detect application failure via synthetic probe and alert.
2. Record current context, Git revision and GitOps sync status.
3. Inspect Deployment, Service, EndpointSlice and events.
4. Identify the bad commit or configuration.
5. Revert through a reviewed Git change; trigger reconciliation if needed.
6. Verify healthy endpoints, traffic, p95 latency and error rate.
7. Record time to detect, time to recover and prevention action.

```powershell
kubectl get deployment,svc,endpointslice -n tenant-alpha
kubectl get events -n tenant-alpha --sort-by=.lastTimestamp
kubectl rollout status deployment/alpha-api -n tenant-alpha --timeout=180s
```

If GitOps is unavailable, follow a preapproved break-glass process, preserve audit evidence, and reconcile emergency changes back to Git as soon as safely possible.

## 18. Observability and reliability acceptance (Lab 15)

Create a dashboard with GitOps reconciliation failures, admission denials, tenant CPU/memory usage, quota consumption, pending Pods, restarts, network-denied traffic where supported, application availability and cost variance.

Establish numeric SLO thresholds **before** the test. Record baseline and post-change p95 latency, errors, recovery duration and any customer impact. Do not claim that an alert works unless a controlled trigger was observed and the notification path verified.

## 19. Final review and acceptance report (Lab 16)

| Control | Positive test | Negative test | Evidence |
|---|---|---|---|
| GitOps reconciliation | Approved commit deploys | Drift corrected/detected | Revision, sync events |
| RBAC | Alpha deployer edits alpha Deployment | Alpha deployer denied in beta | `auth can-i`, API response |
| Pod Security | Restricted-compliant Pod admitted | Privileged Pod rejected | Events, policy labels |
| NetworkPolicy | Approved service/DNS reachable | Cross-tenant path blocked | Client probes, CNI evidence |
| Admission policy | Approved manifest admitted | Missing labels/unsafe image denied | Admission error, policy |
| Resource governance | Valid workload schedules | Excess request denied | Quota and events |
| Cost attribution | Tenant allocation reconciles | Idle/shared not double-counted | Billing comparison |
| Reliability | Health and SLO within target | Bad config detected and reverted | Timeline, metrics |

**Exit criteria:**
- [ ] All 16 labs executed in an authorized disposable staging environment.
- [ ] GitOps scope, permissions and branch protections reviewed.
- [ ] Two tenants created with owner/cost labels and least-privilege access.
- [ ] Both allowed and denied RBAC/network/admission tests passed.
- [ ] Quotas and Pod Security controls verified.
- [ ] Cost allocation reconciled to provider billing within a documented tolerance.
- [ ] Recovery drill completed with measured detection and recovery times.
- [ ] Application SLOs and minimum redundancy preserved.
- [ ] Evidence linked to immutable Git revisions and dated results.
- [ ] Independent reviewer signs off on findings and remaining risks.

A published draft is **not** a completed or lab-validated project. Update the tracker only after executing and reviewing the exercises.

## 20. Cleanup and rollback

Use GitOps to remove test-only application resources and policy objects in reverse dependency order. Verify no controller or shared workload depends on the resources. Namespace deletion destroys namespaced workloads and may remove PVC objects; never use it on production or shared namespaces.

```powershell
kubectl config current-context
kubectl get all -n tenant-alpha
kubectl get pvc -n tenant-alpha
kubectl get all -n tenant-beta
kubectl get pvc -n tenant-beta
```

For a disposable cluster, decommission it only after preserving required evidence and checking cloud resources that may remain billable. Remove cloud disks, load balancers and snapshots only through approved retention and deletion procedures.

## 21. Capstone reflection and production handoff

Summarize architectural decisions, threat model, ownership, policy exceptions, cost-allocation assumptions, SLOs, rollback mechanisms, unresolved gaps and future platform improvements. Convert successful lab artifacts into reviewed production templates rather than copying staging values without capacity/security analysis.

**Part 19 writing milestone:** Chapters 091–095 have been drafted; runtime validation and independent technical review remain outstanding.

**Next:** Chapter 096 — CRDs, Operators and Custom Controllers, beginning Part 20 — Advanced Platform Engineering and Production Operations.
