# Chapter 092 — Policy as Code with Kyverno and Gatekeeper

**Track:** Kubernetes Administration · **Part 19 — GitOps and Platform Automation**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** Kubernetes administrators, SREs, platform and security engineers  
**Prerequisites:** Chapters 041–045 and 091; kubectl, Helm, Git, PowerShell, disposable staging cluster.

## Learning outcomes
Explain admission control; compare Kyverno and OPA Gatekeeper; create, audit, enforce, test and troubleshoot policies; integrate policy changes with GitOps; manage exceptions and recovery safely.

## 1. Architecture and operational boundaries
API request → authentication → authorization → mutating admission → validating admission → persistence. Kyverno evaluates Kubernetes-native policies and can mutate, validate, generate and verify images depending on installed features and policy type. Gatekeeper uses OPA/Rego with ConstraintTemplates and Constraints. Neither replaces RBAC, Pod Security Admission, image scanning or runtime detection. Webhook failurePolicy, timeoutSeconds, namespace exclusions and controller availability affect application availability.

**Safety:** Use a dedicated disposable cluster and namespace. Begin in Audit mode. Pin controller/chart versions after compatibility review. Do not install two overlapping enforcing policies in production without ownership and failure-mode review. Avoid blanket exclusions of security-sensitive namespaces. Validate webhook availability and API-server behavior before enforcing.

## 2. Prepare a staging environment (Lab 01)
PowerShell:
```powershell
kubectl config current-context
kubectl cluster-info
kubectl create namespace policy-lab --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace policy-lab environment=staging --overwrite
kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations
helm version
```
**Expected:** Context confirmed, staging namespace exists, Helm accessible. Stop if context points to production.

## 3. Install Kyverno (Lab 02)
Use the official chart repository, select a reviewed version and check compatibility with the cluster version:
```powershell
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update
helm search repo kyverno/kyverno --versions
# Replace <APPROVED_CHART_VERSION> with the tested version.
helm upgrade --install kyverno kyverno/kyverno -n kyverno --create-namespace --version <APPROVED_CHART_VERSION> --wait --timeout 10m
kubectl get pods -n kyverno
kubectl get validatingwebhookconfigurations | Select-String kyverno
```
**Expected:** Controller pods Ready and admission webhook registered. Record chart, app, Kubernetes and policy API versions before continuing.

## 4. Audit required labels with Kyverno (Lab 03)
Save as `kyverno-require-team.yaml`:
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-team-label-lab
spec:
  background: true
  validationFailureAction: Audit
  rules:
    - name: require-team
      match:
        any:
          - resources:
              kinds: ["Pod"]
              namespaces: ["policy-lab"]
      validate:
        message: "Pods must declare metadata.labels.team"
        pattern:
          metadata:
            labels:
              team: "?*"
```
```powershell
kubectl apply -f .\kyverno-require-team.yaml
kubectl run unlabeled-test --image=nginx:stable --restart=Never -n policy-lab
kubectl get policyreport -n policy-lab
kubectl get clusterpolicy require-team-label-lab -o yaml
```
**Expected:** Pod is admitted in Audit mode; policy report eventually records the violation. Reporting is asynchronous. PolicyReport API availability depends on installed controllers. Delete test Pod before next lab.

## 5. Enforce after verifying scope (Lab 04)
Edit policy to `validationFailureAction: Enforce`, reapply and try creating a Pod without the label:
```powershell
kubectl delete pod unlabeled-test -n policy-lab --ignore-not-found
kubectl apply -f .\kyverno-require-team.yaml
kubectl run unlabeled-test --image=nginx:stable --restart=Never -n policy-lab
kubectl run labeled-test --image=nginx:stable --restart=Never -n policy-lab --labels=team=platform
```
**Expected:** Unlabeled Pod rejected, labeled Pod admitted. Check effective policy configuration and webhook readiness if behavior differs. Note that updates to existing objects and controller-created Pods require separate testing.

## 6. Gatekeeper installation (Lab 05)
Use a separate disposable cluster or ensure no conflicting enforced policy:
```powershell
helm repo add gatekeeper https://open-policy-agent.github.io/gatekeeper/charts
helm repo update
helm search repo gatekeeper/gatekeeper --versions
helm upgrade --install gatekeeper gatekeeper/gatekeeper -n gatekeeper-system --create-namespace --version <APPROVED_CHART_VERSION> --wait --timeout 10m
kubectl get pods -n gatekeeper-system
kubectl get validatingwebhookconfigurations | Select-String gatekeeper
```
**Expected:** Gatekeeper controllers Ready. Verify API compatibility and chart values before production use.

## 7. Write a ConstraintTemplate (Lab 06)
Save as `template-required-team.yaml`:
```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequiredteam
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredTeam
      validation:
        openAPIV3Schema:
          type: object
          properties: {}
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiredteam
        violation[{"msg": msg}] {
          input.review.kind.kind == "Pod"
          not input.review.object.metadata.labels.team
          msg := "Pod requires team label"
        }
```
```powershell
kubectl apply -f .\template-required-team.yaml
kubectl get constrainttemplates
kubectl wait --for=condition=Established crd/k8srequiredteam.constraints.gatekeeper.sh --timeout=120s
```
**Expected:** Constraint CRD established. Rego syntax and ConstraintTemplate API must be tested against the installed Gatekeeper release.

## 8. Audit and enforce Gatekeeper constraints (Lab 07)
Save as `constraint-required-team.yaml`:
```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredTeam
metadata:
  name: required-team-staging
spec:
  enforcementAction: dryrun
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    namespaces: ["policy-lab"]
```
```powershell
kubectl apply -f .\constraint-required-team.yaml
kubectl get k8srequiredteam required-team-staging -o yaml
```
**Expected:** Existing violations appear under constraint status after audit processing. Change `dryrun` to `deny` only after reviewing exceptions and observing expected matches; test a new unlabeled Pod. To avoid ambiguity, disable the overlapping Kyverno Enforce policy before comparing rejection messages.

## 9. Image registry controls (Lab 08)
Design policy to permit only reviewed image registries, including registry host, tag/digest format and mirror conventions. Audit existing Pods and controllers before enforcement. Test approved, unapproved and digest-pinned images. Prefer digest pinning and signature verification where supported. A registry-name allowlist alone does **not** prove image trustworthiness.

## 10. Security context and resource governance (Lab 09)
Develop staging policies to require non-root containers, disallow privilege escalation, restrict privileged/hostPath usage, and require CPU/memory requests and limits. Test Deployments, Jobs, CronJobs and init containers; check interaction with Pod Security Admission and LimitRanges. Avoid blanket rules that break system workloads.

## 11. GitOps promotion and change control (Lab 10)
Suggested repository:
```text
kubernetes/
  policies/
    kyverno/
      base/
      overlays/staging/
      overlays/production/
    gatekeeper/
      templates/
      constraints/staging/
      constraints/production/
    tests/
    runbooks/
```
Submit policy changes by PR with security/platform review, YAML/schema checks, policy unit tests and staging admission tests. Promote immutable reviewed revisions. Separate controller upgrades from policy enforcement changes. Use Audit/dryrun → review violations → scoped Enforce/deny. Do not automatically sync experimental deny policies to production.

## 12. Exceptions and emergency recovery (Lab 11)
Exception requests require owner, business justification, affected namespace/workload, expiry, compensating controls and approval. Prefer tightly scoped exclusions and a tracked Git change. During an incident:
1. Identify rejected API requests and the responsible webhook/policy from events, audit logs and controller logs.
2. Verify webhook endpoint readiness, CA bundle, certificates, timeout and network reachability.
3. Roll back the offending **policy** in Git, reconcile and confirm admission is restored.
4. If the webhook itself is unavailable, follow the approved emergency procedure for webhook failure policy or controller recovery; record any temporary reduction in enforcement.
5. Remove emergency exemptions after recovery and perform an RCA.

Never blindly delete all admission webhooks or disable protections cluster-wide.

## 13. Troubleshooting commands (Lab 12)
```powershell
kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations
kubectl get pods -n kyverno
kubectl get pods -n gatekeeper-system
kubectl get clusterpolicies
kubectl get constrainttemplates
kubectl get events -n policy-lab --sort-by=.lastTimestamp
kubectl logs -n kyverno deployment/kyverno-admission-controller --tail=100
kubectl logs -n gatekeeper-system -l control-plane=controller-manager --tail=100
```
Deployment and label names vary by release: inspect actual resources before running log commands. Diagnose webhook timeout versus policy denial, TLS failure, API incompatibility, namespace match errors and stale background audit reports separately.

## 14. Incident simulation (Lab 13)
In staging, deliberately create a policy denying an otherwise valid test Pod. Capture the denial message, policy name, Git revision, time to detection, rollback commit and time to recovery. Confirm approved workloads remain admitted and rejected workloads are rejected only where expected. Never use critical system namespaces for the simulation.

## 15. Operational acceptance (Lab 14)
- [ ] Controllers healthy, versions recorded and upgrades documented.
- [ ] Audit mode shows expected violations without unexpected denials.
- [ ] Enforce mode rejects a negative test and permits a positive test.
- [ ] Namespace, workload and exception boundaries verified.
- [ ] Admission webhook outage behavior reviewed and exercised safely.
- [ ] GitOps PR, promotion, rollback and reconciliation tested.
- [ ] Alerts, policy reports, logs and incident runbooks verified.
- [ ] Independent technical review and runtime validation recorded.

## Cleanup
```powershell
kubectl delete clusterpolicy require-team-label-lab --ignore-not-found
kubectl delete k8srequiredteam required-team-staging --ignore-not-found
kubectl delete constrainttemplate k8srequiredteam --ignore-not-found
kubectl delete namespace policy-lab --ignore-not-found
```
Uninstall controllers only in a disposable lab after checking that no other workloads or policies depend on them.

## Production takeaways
Treat policies as production code. Audit first, enforce gradually, scope narrowly, preserve availability, require PR reviews, test recovery, and keep evidence of admission behavior. This chapter is a written draft, **not** proof that the labs were executed.

**Next:** Chapter 093 — Multi-Tenancy and Namespace Governance.
