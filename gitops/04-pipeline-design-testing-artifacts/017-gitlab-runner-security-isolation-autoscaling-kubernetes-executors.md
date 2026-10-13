# Chapter 017 — GitLab Runner Security, Isolation, Autoscaling and Kubernetes Executors

**Part 04 — Pipeline Design, Testing and Artifacts** | **Chapter 017 / 100**  
**Audience:** SREs, DevSecOps, Kubernetes and platform engineers  
**Platforms:** GitLab Runner, Kubernetes, AWS EKS, Azure AKS, Google GKE  
**Lab:** Dedicated disposable Kubernetes namespace, GitLab Runner Helm chart, isolated training project  
**Reference environment:** Dev, Test, Staging and Production share one Kubernetes cluster as separate namespaces. CI runner workloads must not gain production namespace privileges.

> **Safety boundary:** Use an authorized training cluster or isolated node pool. Do not install the lab runner in a production namespace, give its service account cluster-admin, mount host Docker sockets or supply cloud production credentials. Helm/Kubernetes commands below create resources: review the target context first.

## 1. Objectives

1. Describe the threat model for CI runners executing untrusted repository code.
2. Apply runner scope, tags, protected refs, Kubernetes RBAC, service accounts and pod security.
3. Deploy a nonprivileged GitLab Runner with the Kubernetes executor using a Helm values file.
4. Set pod resource requests/limits, namespace isolation and network boundaries.
5. Understand autoscaling via runner job concurrency and Kubernetes node provisioning.
6. Diagnose runner scheduling, image pulls, RBAC, quotas, token errors and pending jobs.
7. Design separated MR, trusted-build and release runner pools for EKS/AKS/GKE.
8. Produce operational evidence and cleanup safely.

## 2. Architecture and trust boundaries

```text
                   GitLab project / group
                           |
                   GitLab job scheduler
                           |
                  runner authentication
                           |
             +-------------+--------------+
             |                            |
     MR validation runner           Trusted release runner
     isolated namespace             separately managed
     untrusted source code          protected refs + approvals
             |                            |
      Kubernetes executor          dedicated runner/identity
             |                            |
     Ephemeral job pod              restricted release job
             |                            |
   no cloud production access       GitOps promotion MR only
             |
   Kubernetes node pool / autoscaler
             |
   Shared cluster: demo-dev | demo-test | demo-staging | demo-prod
```

**Important:** Kubernetes namespaces provide administrative boundaries but share the cluster control plane and potentially worker nodes. For high-risk untrusted code, prefer a separate CI cluster or stronger isolation, not merely a namespace.

## 3. Runner security threat model

| Threat | Failure mode | Mitigation |
| --- | --- | --- |
| Untrusted MR code | Exfiltrates available variables or tokens | No privileged secrets on MR runners |
| Privileged containers | Escapes expected container boundary | Disable privileged mode, host mounts and host namespaces |
| Overbroad Kubernetes RBAC | Creates or reads resources outside CI namespace | Namespaced, minimal runner service account |
| Shared caches | Cross-branch cache poisoning | Separate trusted/untrusted cache namespaces and keys |
| Broad network access | Reaches metadata endpoints or production services | Default-deny policies plus approved egress |
| Runner token theft | Impersonates runner manager | Secure token storage, rotation and revocation |
| Unbounded concurrency | Starves application nodes | Quotas, limits, dedicated node pools and capacity planning |
| Mutable images | Unexpected tooling drift | Pin images by digest for production |
| Host Docker socket | Host-level control from job | Do not mount Docker socket into MR jobs |
| Insecure artifact transfer | Sensitive output disclosure | Restrict artifacts and avoid credentials |

Protected runner settings and project scopes are helpful controls, **not** a substitute for isolated infrastructure and least-privilege identity.

## 4. Kubernetes executor lifecycle

1. GitLab creates an eligible pipeline job.
2. A registered runner requests the job.
3. Kubernetes executor creates a job pod using the runner's Kubernetes API permissions.
4. Init/helper/build containers perform checkout and execute the script.
5. GitLab receives status, traces and configured artifacts.
6. Runner deletes the completed job pod according to executor behavior and cleanup settings.

Job pod creation requires Kubernetes API permissions; grant only the verbs/resources needed by the installed runner version and selected features. Features such as informer-based pod monitoring or namespace-per-job can change required permissions.

## 5. Kubernetes security baseline

### Dedicated namespace

```bash
kubectl config current-context
kubectl get nodes
kubectl create namespace ci-training
kubectl label namespace ci-training \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted
```

**Compatibility:** Some runner helper/build images, volume permissions and execution modes may need adjustments under Restricted Pod Security. Validate with the actual runner/chart version. Never silently weaken admission policies to make the lab pass.

### ResourceQuota

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: ci-training-quota
  namespace: ci-training
spec:
  hard:
    pods: "12"
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
```

Save as `quota.yaml`, then:

```bash
kubectl apply -f quota.yaml
kubectl -n ci-training describe resourcequota ci-training-quota
```

Ensure all job pods and runner manager resources have compatible requests/limits.

### LimitRange

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: ci-training-limits
  namespace: ci-training
spec:
  limits:
    - type: Container
      defaultRequest:
        cpu: 100m
        memory: 128Mi
      default:
        cpu: "1"
        memory: 1Gi
```

Save as `limits.yaml` and apply.

### NetworkPolicy baseline

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ci-training-default-deny
  namespace: ci-training
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

A default-deny policy blocks DNS, GitLab, registry and Kubernetes API egress **if the cluster CNI enforces NetworkPolicy**. Do **not** apply it before establishing the required allow policies and testing connectivity. Exact DNS selectors, API endpoint paths and egress destinations depend on the cluster/CNI. An unrestricted `0.0.0.0/0` egress allow rule would defeat much of the boundary.

For the introductory lab, first verify that the CNI supports policies and use an approved, tested policy set; otherwise document network isolation as **Not Verified** rather than claiming enforcement.

## 6. Install GitLab Runner using Helm

### Prerequisites

- Authorized training cluster with sufficient resources.
- Helm 3, `kubectl`, GitLab project runner creation permissions.
- Kubernetes executor supported by the selected GitLab Runner Helm chart version.
- Egress to GitLab and container registry.
- Runner authentication token created through the modern GitLab UI/API workflow.

### Step 1 — Create project runner

In GitLab project **Settings → CI/CD → Runners**, create a project runner:

- Name: `ci-training-kubernetes`
- Tag: `ci-training-k8s`
- Run untagged: disabled
- Protected: disabled **for this untrusted MR lab only**
- Restrict to disposable training project

Record runner ID and GitLab version. Keep the runner authentication token out of source control.

### Step 2 — Create Kubernetes Secret securely

Read the runner authentication token interactively and create a Secret without writing the value into YAML:

```bash
read -r -s -p "Runner authentication token: " RUNNER_TOKEN
printf '\n'
kubectl -n ci-training create secret generic gitlab-runner-auth \
  --from-literal=runner-token="$RUNNER_TOKEN" \
  --from-literal=runner-registration-token=""
unset RUNNER_TOKEN
```

**Caution:** `--from-literal` can expose the token briefly in local process arguments. Use your organization's approved secret delivery mechanism in real deployments. The secret key requirements shown reflect commonly used chart versions; check the selected chart's documented `runners.secret` schema before applying. Do not expose Secret contents in logs.

### Step 3 — Add chart repository and inspect values

```bash
helm repo add gitlab https://charts.gitlab.io
helm repo update
helm show values gitlab/gitlab-runner > chart-default-values.yaml
helm show chart gitlab/gitlab-runner
```

Record and pin an approved chart version for repeatable deployments. The command above discovers the latest chart only for evaluation.

### Step 4 — Create `runner-values.yaml`

```yaml
gitlabUrl: https://gitlab.example.com
runners:
  secret: gitlab-runner-auth
  tags: "ci-training-k8s"
  runUntagged: false
  locked: true
  config: |
    [[runners]]
      executor = "kubernetes"
      limit = 2
      [runners.kubernetes]
        namespace = "ci-training"
        image = "python:3.12-slim"
        privileged = false
        poll_timeout = 180
        cpu_request = "100m"
        cpu_limit = "1"
        memory_request = "128Mi"
        memory_limit = "1Gi"
        helper_cpu_request = "100m"
        helper_cpu_limit = "500m"
        helper_memory_request = "128Mi"
        helper_memory_limit = "512Mi"
        service_cpu_request = "100m"
        service_cpu_limit = "500m"
        service_memory_request = "128Mi"
        service_memory_limit = "512Mi"
        [runners.kubernetes.pod_security_context]
          run_as_non_root = true

concurrent: 2

rbac:
  create: true

serviceAccount:
  create: true

resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

**Version note:** Chart values and runner configuration keys change across releases. Some modern runner creation attributes, such as tags/locked status, are managed by GitLab at runner creation rather than registration. Verify the effective chart template and server-side runner settings; do not assume `runners.tags` changes an existing `glrt-` runner's tags.

**Pod Security note:** `run_as_non_root` alone does not guarantee every helper/build container satisfies the Restricted profile. Validate actual pod admission, security contexts and images; if denied, use approved runner/image configuration and isolated lab policy rather than disabling production protections.

### Step 5 — Render and inspect before installation

```bash
helm template ci-training-runner gitlab/gitlab-runner \
  --namespace ci-training \
  -f runner-values.yaml > rendered-runner.yaml

kubectl apply --dry-run=server -f rendered-runner.yaml
```

Server-side dry run may fail if rendered resources depend on installation-time ordering, hooks or API availability; investigate rather than assuming security failure or success. Inspect rendered ServiceAccount, Role/RoleBinding, Deployment and any ClusterRole objects. Confirm no cluster-admin grants or unexpected privileges.

### Step 6 — Install into disposable namespace

```bash
helm upgrade --install ci-training-runner gitlab/gitlab-runner \
  --namespace ci-training \
  --create-namespace \
  -f runner-values.yaml \
  --wait --timeout 5m

kubectl -n ci-training get deployments,pods,serviceaccounts
kubectl -n ci-training get roles,rolebindings
helm -n ci-training status ci-training-runner
```

The manager deployment may be healthy while job pod creation is still blocked by RBAC, network or admission policies. Verify with a real pipeline.

## 7. Hands-on lab — run a Kubernetes executor job

Create a disposable GitLab project repository:

```text
demo-app/
├── .gitlab-ci.yml
├── README.md
└── tests/
    └── test_runner.py
```

`tests/test_runner.py`:

```python
import os
import unittest


class RunnerTests(unittest.TestCase):
    def test_gitlab_context(self):
        self.assertTrue(os.environ.get("CI_JOB_ID"))

    def test_basic_math(self):
        self.assertEqual(2 * 3, 6)


if __name__ == "__main__":
    unittest.main()
```

`.gitlab-ci.yml`:

```yaml
workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
    - when: never

stages: [validate, test]

default:
  image: python:3.12-slim
  tags:
    - ci-training-k8s

runner_info:
  stage: validate
  script:
    - python --version
    - python -c 'import os; print("Runner ID present:", bool(os.getenv("CI_RUNNER_ID")))'

unit_tests:
  stage: test
  needs: [runner_info]
  script:
    - python -m unittest discover -s tests -v
```

`README.md`:

```markdown
# demo-app

Disposable Kubernetes executor runner security lab.
```

Commit to a feature branch and open an MR:

```bash
git clone https://gitlab.example.com/training/demo-app.git
cd demo-app
git switch main
git pull --ff-only origin main
git switch -c feature/ch017-kubernetes-runner
# Add the lab files
git add .gitlab-ci.yml README.md tests/
git commit -m "ci: test isolated Kubernetes runner"
git push -u origin feature/ch017-kubernetes-runner
```

Expected: both jobs succeed and GitLab job details identify the `ci-training-k8s` runner.

## 8. Verify Kubernetes isolation

### Inspect pod lifecycle

While the pipeline runs:

```bash
kubectl -n ci-training get pods -w
```

In a separate terminal:

```bash
kubectl -n ci-training get events --sort-by=.lastTimestamp
kubectl -n ci-training describe resourcequota ci-training-quota
```

### Verify runner service account authorization

Find the actual runner manager ServiceAccount from the Helm release and use its name:

```bash
kubectl -n ci-training get serviceaccounts
kubectl auth can-i create pods \
  --as=system:serviceaccount:ci-training:<RUNNER_SERVICE_ACCOUNT> \
  -n ci-training
kubectl auth can-i list secrets \
  --as=system:serviceaccount:ci-training:<RUNNER_SERVICE_ACCOUNT> \
  -n demo-prod
kubectl auth can-i create deployments \
  --as=system:serviceaccount:ci-training:<RUNNER_SERVICE_ACCOUNT> \
  -n demo-prod
```

Replace `<RUNNER_SERVICE_ACCOUNT>` with the actual value. These impersonation checks require operator permission to impersonate identities; a `Forbidden` error from your own operator account is **not** evidence that the runner identity lacks access. Use an authorized RBAC reviewer or inspect RoleBindings and ClusterRoleBindings if impersonation is unavailable.

Expected security posture: job-pod creation in `ci-training` is permitted, while reading secrets and creating deployments in `demo-prod` are denied.

**Important:** The Kubernetes executor's manager identity and job pod identity can differ. Inspect both. A job pod should not receive unnecessary Kubernetes API access; disable automatic service-account token mounting where compatible with your runner and workflow.

## 9. Negative tests

### Test A — Runner tag mismatch

Temporarily change `ci-training-k8s` to `ci-training-no-match` in the disposable MR job. Expected: pending job. Restore the tag and verify recovery.

### Test B — Quota pressure

Do not exhaust a shared cluster. On a dedicated lab namespace, lower a disposable quota only if no other workload depends on it; observe a job pod admission failure and restore the original quota. Prefer a separate test namespace when possible. Expected: clear quota event and runner retry/failure diagnostics.

### Test C — RBAC denial

Using the authorized operator identity, verify that the runner's service account cannot create deployments in `demo-prod`. Do not actually attempt a privileged deployment as the runner.

### Test D — Network policy

Apply a reviewed default-deny policy **only after** the required DNS, GitLab, registry and Kubernetes API allow rules are in place. Verify that the job can still reach approved endpoints and cannot reach an explicitly designated test endpoint. If the CNI cannot enforce policies, mark this test **Not Verified**.

### Test E — Pod security admission

Inspect actual job pod security contexts and admission events. If the Restricted profile rejects pods, correct approved runner/image settings. Do not loosen production namespace policies to pass.

## 10. Autoscaling and capacity planning

Two distinct layers matter:

1. **Runner concurrency:** How many jobs a runner manager accepts (`concurrent`, runner `limit`, request concurrency and GitLab-side scheduling).
2. **Kubernetes node capacity:** Whether the cluster has nodes with enough CPU/memory and compatible selectors/taints for job pods.

Kubernetes Cluster Autoscaler, Karpenter on EKS, AKS cluster autoscaler or GKE node autoscaling can add capacity, subject to provisioning time, quotas, maximum sizes and cloud limits. The runner Helm chart alone does not guarantee node autoscaling.

### Sizing example

Suppose each job requests 500m CPU and 1 GiB memory and the dedicated CI node pool has 8 allocatable CPU and 24 GiB allocatable memory after overhead. CPU theoretically accommodates 16 such pods and memory 24; CPU is the tighter simple bound. Actual capacity is lower due to manager pods, system overhead, quotas, affinity, topology and daemonsets. Do not use this calculation as a deployment guarantee.

### Autoscaling controls

- Use a dedicated CI node pool with labels, taints and tolerations.
- Bound job pod CPU/memory requests and limits.
- Cap runner concurrency and namespace quotas.
- Measure p95 queue time and pod scheduling latency.
- Review scale-up latency and scale-down disruption.
- Prefer short-lived isolated credentials and disposable runners.
- Prevent untrusted CI jobs from landing on production application nodes.

## 11. Multi-cloud reference patterns

| Platform | Runner node capacity | Identity | Security priorities |
| --- | --- | --- | --- |
| EKS | Dedicated managed node group / Karpenter NodePool | IRSA or EKS Pod Identity | Restrict IAM trust and IMDS exposure |
| AKS | Dedicated node pool / cluster autoscaler | Microsoft Entra Workload ID | Federated identity, node/network isolation |
| GKE | Dedicated node pool / autoscaler | Workload Identity Federation for GKE | IAM scope, metadata access, node isolation |

The lab is cloud-neutral; production implementations must adapt service accounts, network policies, node selectors, autoscaler settings and IAM trust per provider. Keep CI identities separate from runtime workload identities.

## 12. Troubleshooting runbook

| Symptom | Likely cause | Investigation |
| --- | --- | --- |
| Job pending in GitLab | No eligible runner, tags, protection | Check runner ID, scope and tags |
| Runner manager CrashLoopBackOff | Invalid config, missing token, resources | Inspect pod events and sanitized logs |
| Job pod not created | RBAC or API errors | Review Role/RoleBinding and runner logs |
| Job pod Pending | Quota, taint, insufficient capacity | Inspect pod events and node autoscaler |
| Pod rejected | Restricted admission policy | Review securityContext and images |
| ImagePullBackOff | Registry/DNS/credentials | Inspect image pull events and egress |
| Script cannot reach GitLab | DNS/NetworkPolicy/proxy | Validate approved egress and TLS |
| Runner auth fails | Token revoked/rotated or URL mismatch | Check GitLab runner state and Secret |
| Unexpected production access | Overbroad SA/RoleBinding/identity | Quarantine runner and remove access |
| Autoscaler not adding nodes | Limits, quotas, incompatible pod scheduling | Check cloud autoscaler logs and constraints |

## 13. Incident response and rollback

1. Identify affected runner ID, Helm release, namespace, service account and jobs.
2. If compromise suspected, pause runner in GitLab and revoke exposed credentials.
3. Preserve authorized, nonsecret logs and Kubernetes events.
4. Inspect effective RBAC, service account token mounting and network policies.
5. Restore with reviewed Helm values and a controlled `helm upgrade` or rollback.
6. Validate with an unprivileged training pipeline before resuming trusted work.

Helm rollback example (review revision and values first):

```bash
helm -n ci-training history ci-training-runner
helm -n ci-training rollback ci-training-runner <KNOWN_GOOD_REVISION>
```

Never rollback blindly across runner authentication or Kubernetes API compatibility changes.

## 14. Cleanup

Only in the disposable training namespace:

```bash
helm -n ci-training uninstall ci-training-runner
kubectl -n ci-training delete resourcequota ci-training-quota --ignore-not-found
kubectl -n ci-training delete limitrange ci-training-limits --ignore-not-found
kubectl -n ci-training delete secret gitlab-runner-auth --ignore-not-found
```

Delete the server-side runner object through the supported GitLab UI/API and verify retirement. Remove the namespace **only after** checking it contains no other resources:

```bash
kubectl -n ci-training get all
kubectl -n ci-training get pvc,secret,configmap
```

Do not delete a shared namespace. Remove temporary local files containing sensitive configuration and dispose of the training infrastructure under your organization's procedure.

## 15. Acceptance checklist

- [ ] Dedicated runner namespace and project scope verified.
- [ ] Authentication token not committed or logged.
- [ ] Kubernetes executor configured nonprivileged.
- [ ] Runner manager RBAC reviewed for least privilege.
- [ ] Job pods have appropriate security context and bounded resources.
- [ ] Successful GitLab MR pipeline executed on intended runner.
- [ ] Unmatched-tag negative test reproduced and resolved.
- [ ] No runner identity access to production namespace secrets or deployments.
- [ ] NetworkPolicy enforcement tested or explicitly marked Not Verified.
- [ ] Pod Security admission validated without weakening production controls.
- [ ] Runner and node autoscaling limits documented.
- [ ] EKS, AKS and GKE workload identity differences understood.
- [ ] Rollback and runner retirement procedures recorded.

## 16. Evidence template

```text
CHAPTER 017 — KUBERNETES RUNNER SECURITY LAB
Date:
GitLab version/tier:
Runner chart version:
Cluster/provider:
Namespace:
Runner ID:
Runner service account:
MR URL / pipeline ID:
Successful jobs:
Privileged mode:
Pod security enforcement:
Runner RBAC production-denial test:
Network policy test:
Quota/limits:
Observed pending and scheduling time:
Autoscaler type and max capacity:
Tag mismatch test:
Cleanup / runner retirement:
Reviewer:
Open risks and owners:
```

## 17. Knowledge checks

1. Why is namespace isolation insufficient for hostile CI workloads?
2. What permissions does the Kubernetes executor manager need, and how do they differ from job pod permissions?
3. Why can a healthy runner manager still fail to execute jobs?
4. What is the difference between runner concurrency and Kubernetes node autoscaling?
5. Why should MR and release runners use separate identities and infrastructure?
6. How do workload identity patterns differ across EKS, AKS and GKE?
7. Why must NetworkPolicy enforcement be verified against the actual CNI?

## 18. Completion

**Pass:** An authorized isolated Kubernetes runner successfully executes the MR pipeline, least-privilege RBAC is verified, negative scheduling tests are documented, and the runner is retired safely.

**Next: Chapter 018 — GitLab CI/CD Reusable Pipelines, Includes, Templates and Child Pipelines.**
