# Chapter 048 — Jenkins on Amazon EKS: IAM, IRSA/Pod Identity, Autoscaling and Operations

**Part 10 — Jenkins on Kubernetes, EKS and AKS**  
**Audience:** Jenkins SRE, AWS platform, Kubernetes, security and FinOps engineers  
**Prerequisites:** Chapters 046–047, disposable EKS cluster, AWS CLI v2, kubectl, Helm, scoped AWS IAM permissions.

## Objectives

Operate Jenkins dynamic agents on Amazon EKS using scoped Kubernetes and AWS identities, understand IRSA versus EKS Pod Identity, provision and scale agents with Karpenter or Cluster Autoscaler, secure AWS integrations, investigate production incidents and measure cost and reliability.

## 1. Architecture

```text
Git → Jenkins controller (dedicated EKS namespace, PVC)
           │
           ├─ Kubernetes plugin → EKS API
           │                      ↓
           │             ephemeral agent Pods
           │                ├─ test-only SA (no AWS role)
           │                ├─ S3 artifact SA (scoped role)
           │                └─ release SA (separate trusted jobs)
           │
           └─ CloudWatch/Prometheus → SLO alerts
                              ↓
            EKS managed node groups / Karpenter capacity
```

Keep the controller's Kubernetes API provisioner identity separate from build Pod service accounts. Avoid using one AWS role for all agents or granting production ECR/EKS permissions to untrusted pull-request jobs.

## 2. Identity: Kubernetes RBAC versus AWS IAM

Kubernetes RBAC authorizes Pod lifecycle operations against the Kubernetes API. AWS IAM authorizes AWS API calls such as S3/ECR. They are different control planes.

| Mechanism | How it works | Key controls |
|---|---|---|
| IRSA | Projected OIDC token exchanged through STS `AssumeRoleWithWebIdentity` | EKS OIDC provider, role trust scoped to `system:serviceaccount:namespace:name` |
| EKS Pod Identity | EKS Pod Identity Agent and association supply AWS credentials | Association scoped to cluster/namespace/service account; role trusts `pods.eks.amazonaws.com` |
| Node instance role | Node-level AWS access | Not a substitute for per-workload least privilege |
| EKS access entries / aws-auth | Human/controller cluster access | Separate from Pod AWS API permissions |
| Kubernetes RBAC | Namespaced Pod permissions | Separate provisioner and build SAs |

**IRSA and EKS Pod Identity are alternatives**, not identical implementations. EKS Pod Identity has platform prerequisites and supported regions/versions; validate current AWS documentation and cluster support. GovCloud partitions and endpoints must be checked independently.

## 3. IRSA trust-policy example

Create a dedicated role with the EKS cluster's actual OIDC issuer and AWS account ID. Illustrative IAM trust document:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/EXAMPLE"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "oidc.eks.us-east-1.amazonaws.com/id/EXAMPLE:aud": "sts.amazonaws.com",
        "oidc.eks.us-east-1.amazonaws.com/id/EXAMPLE:sub": "system:serviceaccount:jenkins-build:jenkins-artifacts"
      }
    }
  }]
}
```

Replace **every** placeholder with real nonproduction values. Bind the role to only the needed S3 bucket prefix or ECR repository, not `*`. Do not put AWS static access keys in a Jenkinsfile.

IRSA service account example:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: jenkins-artifacts
  namespace: jenkins-build
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/jenkins-ch048-artifacts
```

IRSA requires the projected token to be mounted. Therefore **do not set** `automountServiceAccountToken: false` without verifying how the workload identity token is injected; the EKS IRSA mutating webhook injects a dedicated projected service-account token volume. For AWS API access, verify the actual Pod spec and credential chain. For jobs not requiring AWS, keep token automount disabled.

## 4. EKS Pod Identity alternative

For supported clusters, configure an EKS Pod Identity association for the workload service account and role:

```sh
aws eks create-pod-identity-association \
  --cluster-name "$CLUSTER" \
  --namespace jenkins-build \
  --service-account jenkins-artifacts \
  --role-arn "$ROLE_ARN"
```

Prerequisites: EKS Pod Identity Agent installed and healthy on relevant nodes, an IAM role with appropriate Pod Identity trust policy, AWS CLI permissions to create association, and supported cluster configuration. The role trust uses service principal `pods.eks.amazonaws.com` with `sts:AssumeRole` and `sts:TagSession`, rather than an IRSA OIDC federated principal. Use IAM conditions and scoped permissions per AWS guidance. Do not mix IRSA annotations and Pod Identity associations casually for the same workload; verify which credential provider wins.

## 5. Example Jenkins Pipeline with scoped AWS identity

This template assumes a dedicated service account `jenkins-artifacts` is configured for **one** trusted job, AWS CLI v2 is available in an approved image, and the Jenkins Kubernetes plugin can provision Pods in `jenkins-build`:

```groovy
pipeline {
    agent {
        kubernetes {
            defaultContainer 'aws'
            yaml '''
apiVersion: v1
kind: Pod
spec:
  serviceAccountName: jenkins-artifacts
  restartPolicy: Never
  containers:
    - name: aws
      image: public.ecr.aws/aws-cli/aws-cli:2
      command: ["sleep"]
      args: ["99d"]
      tty: true
      resources:
        requests: {cpu: "200m", memory: "256Mi"}
        limits: {cpu: "1", memory: "1Gi"}
'''
        }
    }
    options { timestamps(); timeout(time: 20, unit: 'MINUTES') }
    stages {
        stage('AWS identity') {
            steps {
                sh 'aws sts get-caller-identity --output json'
            }
        }
        stage('Permission boundary') {
            steps {
                sh '''#!/bin/sh
                    set -eu
                    test -n "$AWS_REGION"
                    aws configure get region || true
                '''
            }
        }
    }
}
```

**Important:** This is a teaching template, not a production-hardened one. Pin the AWS CLI image to an approved digest, verify image entrypoint/shell and nonroot compatibility, enforce security contexts, and validate the injected inbound agent. `aws sts get-caller-identity` proves which principal was selected; it does not prove least privilege. For test-only agents, use an unprivileged service account with no AWS identity.

## 6. IAM least privilege and ECR

ECR push permissions should be repository-scoped where supported; `ecr:GetAuthorizationToken` requires resource `*` but must be restricted through identity/condition controls as appropriate. Separate read-only pull, candidate publisher and production promotion roles. ECR authorization tokens are short-lived; use AWS CLI login rather than embedding static registry passwords.

```sh
aws ecr get-login-password --region "$AWS_REGION" |
  docker login --username AWS --password-stdin \
    "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
```

This command requires Docker and a supported ECR endpoint. In GovCloud, verify partition, account, region and DNS suffix before execution.

## 7. Node capacity and autoscaling

| Component | Purpose | SRE consideration |
|---|---|---|
| EKS managed node group | Stable controller or baseline agent capacity | Patching, drain, AMI |
| Karpenter | Provision nodes for pending Pods | NodePool/EC2NodeClass, disruption budgets |
| Cluster Autoscaler | Scale existing node groups | ASG tags and limits |
| HPA | Scale controller replicas? | **Do not** use HPA to create parallel controllers sharing one JENKINS_HOME |
| ResourceQuota | Bound concurrent agent demand | Align with burst traffic |
| PriorityClass | Scheduling priority | Avoid starving system Pods |
| PDB | Disruption control | Controller availability; not replacement for backups |

Choose Karpenter or Cluster Autoscaler based on supported cluster design and avoid overlapping ownership of the same node capacity. Define explicit CPU/memory/ephemeral-storage requests, node affinity and topology constraints. Spot capacity is suitable only for retryable jobs; release jobs with external side effects require idempotency and careful disruption policy.

## 8. Scheduling example

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: ch048-capacity-test
  namespace: jenkins-build
spec:
  restartPolicy: Never
  serviceAccountName: jenkins-build
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  containers:
    - name: check
      image: busybox:1.36
      command: ["sh", "-c", "echo capacity-ok; sleep 15"]
      resources:
        requests:
          cpu: "250m"
          memory: "128Mi"
        limits:
          cpu: "500m"
          memory: "256Mi"
      securityContext:
        runAsUser: 1000
        runAsNonRoot: true
        allowPrivilegeEscalation: false
        capabilities:
          drop: ["ALL"]
```

Apply only to a disposable namespace and use an approved image digest in production. Validate Pod Security policy and image registry access.

## 9. Observability and cost

Measure Jenkins queue time, agent Pod provisioning latency, Karpenter/Cluster Autoscaler node readiness, AWS STS errors, Pod Identity Agent health, ECR pull/push latency, API throttling, Spot interruption rate, node utilization, NAT/egress charges, EBS/PVC usage and cluster/control-plane cost. Compare p50/p95 startup by workload class and use measured requests to right-size node pools.

## 10. Diagnostic commands

```sh
aws eks describe-cluster --name "$CLUSTER" --region "$AWS_REGION" \
  --query 'cluster.{status:status,version:version,endpoint:endpoint}'
kubectl get pods -n jenkins-build -o wide
kubectl get events -n jenkins-build --sort-by=.lastTimestamp
kubectl get nodes -L karpenter.sh/nodepool
kubectl get pods -n kube-system | grep -E 'karpenter|pod-identity|autoscaler' || true
kubectl auth can-i create pods -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-provisioner
aws sts get-caller-identity
```

For identity diagnosis, run `aws sts get-caller-identity` **inside the relevant agent Pod**, not only on your administrator workstation. The latter reports a different credential chain.

## 11. Troubleshooting matrix

| Failure | Diagnostic | Recovery |
|---|---|---|
| STS AccessDenied | Role trust / identity | Fix exact SA subject or association |
| IRSA no credentials | OIDC/webhook/token | Verify OIDC issuer and projected token |
| Pod Identity no credentials | Agent/association | Repair association and node agent |
| Wrong AWS role | Credential chain | Remove conflicting credentials |
| ECR 403 | IAM/repo policy | Scope correct role |
| ECR 401 | Token expired | Refresh login |
| Pod Pending | Requests/taints/quota | Restore capacity |
| Karpenter no nodes | NodePool/EC2NodeClass | Fix constraints/permissions |
| Cluster Autoscaler idle | ASG tags/limits | Correct configuration |
| Spot interruption | Node events | Retry idempotent work |
| PVC pending | CSI/StorageClass | Repair storage |
| Agent disconnect | Remoting/network | Fix controller route |
| DNS/NAT failure | VPC routes/endpoints | Repair connectivity |
| Throttling | AWS/K8s API metrics | Backoff and reduce burst |
| Unexpected node cost | Idle capacity | Tune consolidation/requests |
| Controller PVC failure | EBS events | Restore supported backup |

## 12. Production runbooks

### A. EKS onboarding
1. Verify cluster, version, VPC endpoints and namespaces.
2. Define provisioner Kubernetes RBAC and separate build SAs.
3. Select IRSA **or** Pod Identity per workload.
4. Scope IAM role to nonproduction AWS resources.
5. Launch synthetic Jenkins agent, verify caller identity and deny unauthorized AWS API calls.
6. Validate autoscaling, metrics, cleanup and rollback.

### B. AWS identity failure
1. Capture Pod SA, projected token/association, AWS SDK chain and STS error.
2. Compare expected versus actual role trust.
3. Repair OIDC/Pod Identity Agent/association without broadening IAM.
4. Verify correct role in a fresh agent Pod.
5. Confirm intended AWS resource access and denied actions.

### C. Capacity incident
1. Capture queue p95, Pending events and node scale-up logs.
2. Inspect requests, taints, topology, quotas and EC2 capacity.
3. Adjust node pools or templates; avoid unsafe controller scaling.
4. Validate agent startup, retry behavior and cost.
5. Record change and SLO recovery.

### D. Spot disruption
1. Identify interrupted node and affected Jenkins build.
2. Check whether job is idempotent and has external side effects.
3. Retry only safe stages; verify artifacts and release state.
4. Rebalance capacity for critical release workloads.
5. Update interruption SLO and policy.

### E. Controller disaster recovery
1. Confirm JENKINS_HOME PVC/backup and configuration state.
2. Prevent two controllers mounting one writable home.
3. Restore using tested supported procedure.
4. Validate credentials references, Kubernetes cloud and agent connectivity.
5. Run synthetic build and record RTO/RPO.

## 13. Acceptance criteria

- [ ] EKS cluster/namespace and identity architecture documented.
- [ ] Build SA cannot create Pods or list Secrets.
- [ ] IRSA or Pod Identity tested with exact expected role.
- [ ] Unauthorized AWS action is denied.
- [ ] Agent Pod scheduling and autoscaling observed.
- [ ] ECR access restricted to required repositories.
- [ ] Spot/capacity and identity failure drills completed.
- [ ] Controller backup and rollback procedure documented.

**Companion:** [Chapter 048 hands-on lab](labs/048-jenkins-amazon-eks-iam-irsa-pod-identity-autoscaling-operations-check.md).  
**Next:** Chapter 049 — Jenkins on Azure AKS: Workload Identity, Node Pools and Operations.
