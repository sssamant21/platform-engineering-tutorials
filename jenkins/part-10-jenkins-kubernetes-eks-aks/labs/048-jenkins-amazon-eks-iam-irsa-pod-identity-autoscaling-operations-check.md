# Chapter 048 — Hands-on Lab: Jenkins on Amazon EKS

**Environment:** Disposable EKS cluster, Jenkins Kubernetes plugin, scoped IAM roles, test S3/ECR resources, AWS CLI v2 and kubectl. AWS resources may incur cost; destroy lab infrastructure after verification.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Inventory | Record cluster, region and version | Baseline |
| 02 | Architecture | Map controller/agent/AWS identities | Diagram |
| 03 | Namespace | Create `jenkins-build` | Namespace |
| 04 | Provisioner SA | Verify Kubernetes Pod lifecycle RBAC | `can-i` |
| 05 | Build SA | Verify no Kubernetes Secrets access | Denied |
| 06 | Identity choice | Document IRSA vs Pod Identity | Decision |
| 07 | Role policy | Scope IAM to test resource | JSON |
| 08 | Trust | Bind exact SA subject/association | Evidence |
| 09 | Agent launch | Start disposable Jenkins Pod | Pod |
| 10 | AWS caller | Run STS inside agent | Role ARN |
| 11 | Positive access | Read approved test resource | Success |
| 12 | Negative access | Attempt unauthorized action | AccessDenied |
| 13 | ECR login | Obtain short-lived token | Result |
| 14 | ECR scope | Test repository-level permissions | Evidence |
| 15 | Node pool | Inspect managed/Karpenter capacity | Nodes |
| 16 | Scheduling | Run burst of small agents | Queue p95 |
| 17 | Scale-down | Confirm idle node cleanup | Metrics |
| 18 | Fault | Inject invalid role/association in test SA | Failure |
| 19 | Recovery | Restore trust and rerun | Success |
| 20 | Cleanup | Delete test resources and review cost | Inventory |

## 12 troubleshooting drills

1. IRSA OIDC trust mismatch.
2. EKS Pod Identity Agent unavailable.
3. Pod Identity association missing.
4. Wrong AWS credential provider selected.
5. S3/ECR AccessDenied.
6. Expired ECR registry token.
7. Pod Pending from quota/taint.
8. Karpenter NodePool mismatch.
9. Cluster Autoscaler node group limit.
10. Spot interruption in a retryable job.
11. Agent remoting connection failure.
12. AWS network/NAT/VPC endpoint failure.

Never disable IAM checks or broaden roles to `AdministratorAccess` for a green test. When an identity method is not available in the cluster, mark its drills blocked and record the prerequisite.

## Example identity and capacity checks

```sh
set -eu
aws eks describe-cluster --name "$CLUSTER" --region "$AWS_REGION" \
  --query 'cluster.{status:status,version:version}'
kubectl get sa -n jenkins-build
kubectl auth can-i list secrets -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-build
kubectl get pods -n jenkins-build -o wide
kubectl get events -n jenkins-build --sort-by=.lastTimestamp
kubectl get nodes -o wide
```

Run `aws sts get-caller-identity` inside the agent Pod to verify its effective IAM role. A workstation STS result is not proof of Pod identity.

## Evidence template

```text
UTC timestamp:
AWS partition/account (redact as needed):
Region / EKS cluster / version:
Jenkins controller/agent namespaces:
Kubernetes provisioner SA:
Build SA / IAM role:
IRSA OIDC issuer or Pod Identity association:
Expected and actual STS role:
Positive AWS action:
Denied AWS action:
ECR repo and authorization outcome:
Node group / autoscaler:
Agent queue and Pod startup:
Fault injection / root cause / recovery:
Cost cleanup verification:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted and documented.
- [ ] 12 drills completed or explicitly blocked.
- [ ] AWS identity scoped to exact workload.
- [ ] Unauthorized AWS action denied.
- [ ] Build Pod has no excess Kubernetes RBAC.
- [ ] ECR permissions limited to intended repo.
- [ ] Agent scheduling/autoscaling observed.
- [ ] No static AWS keys in Jenkinsfile.
- [ ] Test AWS resources cleaned up.
- [ ] Reviewer signs off.

**Related:** [Chapter 048 — Jenkins on Amazon EKS](../048-jenkins-amazon-eks-iam-irsa-pod-identity-autoscaling-operations.md).
