# Chapter 050 — Jenkins on Kubernetes, EKS and AKS Production Operations Capstone

**Part 10 — Jenkins on Kubernetes, EKS and AKS (final capstone)**  
**Audience:** Jenkins SRE, Kubernetes platform, AWS/Azure cloud, security, incident response and FinOps teams  
**Prerequisites:** Chapters 046–049, disposable Kubernetes cluster and optionally nonproduction EKS/AKS clusters.

## Mission and learning outcomes

Prove production-readiness of Jenkins controllers and ephemeral Kubernetes agents across cloud-neutral Kubernetes, Amazon EKS and Azure AKS. Build a repeatable architecture, enforce separate controller/provisioner/build/release identities, test Pod template security, demonstrate autoscaling, instrument SLOs, inject failures, perform a **tested** controller restore, and document cost and recovery. Run destructive drills **only** in disposable lab environments.

## 1. Reference architecture

```text
Protected Git repository
        ↓
Jenkins controller (single active writer, PVC, backup, JCasC)
        │
        ├─ Kubernetes plugin / namespaced provisioner RBAC
        │
        └─ ephemeral agent Pods (distinct trust tiers)
              ├─ untrusted PR: no cloud credentials
              ├─ CI/test: limited artifact access
              └─ trusted release: approved identity/approval
        ↓
Kubernetes scheduler → node autoscaler → EKS/AKS pools
        ↓
Logs/metrics/traces → alerts, incident runbooks, FinOps
```

Never mount one writable JENKINS_HOME into two active controllers. Jenkins core state, plugin compatibility and external credentials references must be recoverable from tested backups.

## 2. Deliverables and ownership

| Deliverable | Owner | Evidence |
|---|---|---|
| Architecture diagram/RACI | Platform | Trust boundaries |
| Controller deployment/config | Jenkins SRE | Chart/JCasC versions |
| Provisioner RBAC | Kubernetes admin | Namespaced Role/Binding |
| Agent templates | CI platform | Generated Pod YAML |
| EKS IRSA/Pod Identity | AWS platform | Exact role/SA binding |
| AKS Workload Identity | Azure platform | Federated issuer/subject/audience |
| SLO dashboards | Observability | Baseline and alerts |
| Autoscaling policy | Capacity/FinOps | Queue and node metrics |
| Backup/restore | SRE | Measured RPO/RTO |
| Incident game day | On-call | Failure and recovery log |

## 3. Cloud-neutral baseline

Create separate namespaces or clearly separated service accounts for Jenkins controller and build Pods. The provisioner identity needs only plugin-required Pod lifecycle verbs in the agent namespace. Agent service accounts should have **no** Kubernetes API permissions unless required, and no automatic service-account token mount for ordinary test jobs.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: jenkins-build
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: jenkins-build
  namespace: jenkins-build
automountServiceAccountToken: false
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: agent-quota
  namespace: jenkins-build
spec:
  hard:
    pods: "20"
    requests.cpu: "8"
    requests.memory: "16Gi"
    limits.cpu: "16"
    limits.memory: "32Gi"
```

Quota numbers are **lab examples**, not universal sizing guidance. Validate effective injected `jnlp` container resource requests and admission controls.

## 4. Dynamic agent smoke Pipeline

```groovy
pipeline {
    agent {
        kubernetes {
            defaultContainer 'node'
            yaml '''
apiVersion: v1
kind: Pod
spec:
  serviceAccountName: jenkins-build
  automountServiceAccountToken: false
  restartPolicy: Never
  securityContext:
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: node
      image: node:22-bookworm-slim
      command: ["sleep"]
      args: ["99d"]
      tty: true
      resources:
        requests: {cpu: "250m", memory: "512Mi"}
        limits: {cpu: "1", memory: "1Gi"}
      securityContext:
        runAsUser: 1000
        runAsGroup: 1000
        runAsNonRoot: true
        allowPrivilegeEscalation: false
        capabilities:
          drop: ["ALL"]
'''
        }
    }
    options {
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
        disableConcurrentBuilds()
    }
    stages {
        stage('Identity') {
            steps { sh 'id; node --version; hostname' }
        }
        stage('Test') {
            steps { sh 'node -e "if (2+2!==4) process.exit(1)"' }
        }
        stage('Evidence') {
            steps {
                sh 'date -u > capstone-evidence.txt'
                archiveArtifacts artifacts: 'capstone-evidence.txt', fingerprint: true
            }
        }
    }
}
```

Prerequisites: Jenkins Kubernetes plugin/cloud configured, `jenkins-build` SA created, suitable agent image available. **Production** images must be pinned by approved digest. Inspect the injected inbound-agent container's UID, security context and token mounts separately; this sample only explicitly hardens the Node tool container.

## 5. EKS identity verification

For AWS workloads, choose **IRSA or EKS Pod Identity** with the correct role trust, service account, agent/node prerequisites and scoped permissions. The controller's Kubernetes Pod provisioner identity must not be reused as an AWS publisher identity.

```sh
aws eks describe-cluster --name "$EKS_CLUSTER" --region "$AWS_REGION" \
  --query 'cluster.{status:status,version:version}'
kubectl auth can-i list secrets -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-build
```

Run `aws sts get-caller-identity` **inside** a trusted test agent Pod to confirm the effective role. Test one authorized operation and one unauthorized operation on disposable resources. Do not confuse workstation AWS identity with agent identity.

## 6. AKS identity verification

For Azure workloads, verify AKS OIDC issuer and Microsoft Entra Workload ID, service-account client ID annotation, Pod label `azure.workload.identity/use: "true"`, and exact federated issuer/subject/audience.

```sh
az aks show -g "$AKS_RG" -n "$AKS_CLUSTER" \
  --query '{oidc:oidcIssuerProfile.issuerUrl,workload:securityProfile.workloadIdentity.enabled}' \
  -o json
```

Verify the projected token and Azure identity **inside** a trusted agent; do not log token content. Grant only scoped Azure RBAC to ACR/artifact resources. Untrusted PR Pods must not inherit cloud credentials.

## 7. Node pool and autoscaling design

| Pool | Placement | Reliability/FinOps controls |
|---|---|---|
| System | Kubernetes components | Stable baseline, reserved capacity |
| Controller | Jenkins controller | Durable PVC, PDB, controlled upgrades |
| CI/test | Retryable ephemeral agents | Autoscaling, quotas, measured requests |
| Trusted release | Restricted approved jobs | On-demand, protected identity |
| Spot/interruptible | Safe idempotent jobs only | Interruption handling and bounded retry |

For EKS, validate Karpenter or Cluster Autoscaler ownership and NodePool/managed node group limits. For AKS, validate user/system node pool limits, Azure VM quota, zones and Spot eviction. Avoid assuming Jenkins queue automatically triggers node scale-up: autoscalers generally respond to unschedulable Pods.

## 8. SLOs and observability

| SLI | How to measure | Lab target |
|---|---|---|
| Agent provisioning success | Successful Pod/agent connections ÷ attempts | ≥99% in synthetic tests |
| Queue wait | Jenkins queue p95 | Establish baseline |
| Agent startup | Pod create → connected p95 | Establish baseline |
| Pod failure | Pending/OOM/Evicted count | Zero unexpected |
| Identity enforcement | Denied unauthorized API actions | 100% denied |
| Backup recovery | Restore duration | Within chosen RTO |
| Data recovery | Latest restored state | Within chosen RPO |
| Agent cleanup | Completed Pod removed | 100% |
| Cost per build | Node/cluster/storage cost ÷ builds | Establish baseline |

These are acceptance targets, **not observed production metrics**. Collect Jenkins metrics, Kubernetes events, kube-state-metrics, node metrics, cloud API/identity errors, PVC health, autoscaler logs, audit logs and cloud billing tags.

## 9. Failure injection plan

| # | Fault | Expected behavior | Recovery |
|---|---|---|---|
| 01 | Provisioner RBAC removed | Pod creation denied | Restore reviewed Role |
| 02 | Build SA granted excess rights | Security check fails | Remove binding |
| 03 | Invalid image digest | Image pull fails | Restore approved image |
| 04 | Pod exceeds quota | Admission rejected | Tune quota/requests |
| 05 | Node affinity mismatch | Pod Pending | Fix placement |
| 06 | Agent container OOM | Build fails, evidence captured | Tune memory |
| 07 | Node drain | Agent interrupted | Safe retry |
| 08 | Controller network disruption | Remoting disconnect | Restore routing |
| 09 | DNS failure | SCM/artifact access fails | Restore DNS |
| 10 | Registry throttling | Pull retries/fails | Bounded backoff |
| 11 | EKS IRSA trust mismatch | STS denied | Correct exact trust |
| 12 | EKS Pod Identity Agent down | Credentials unavailable | Restore agent |
| 13 | AKS federated subject mismatch | Token exchange denied | Correct binding |
| 14 | ACR/ECR role revoked | Registry access denied | Restore least privilege |
| 15 | Autoscaler maximum reached | Pods Pending | Add approved capacity |
| 16 | Spot interruption | Retryable job rescheduled | Validate idempotency |
| 17 | PVC unavailable | Controller not ready | Storage recovery |
| 18 | Backup corrupted | Restore validation fails | Recover alternate backup |
| 19 | Plugin incompatibility | Agent creation/remoting fails | Roll back compatible set |
| 20 | Controller upgrade failure | Availability lost | Roll back/restore |

Never run node drains, credential revocation, PVC failure or controller restore drills against a shared production environment.

## 10. Controller backup and restore acceptance

1. Inventory controller core/plugins, JCasC, job configuration, secrets references and PVC.
2. Capture a **consistent** backup using a supported Jenkins/storage procedure, including secrets and encryption material needed for restore.
3. Stop the test controller before restoring its writable home.
4. Restore into an isolated disposable controller with matching compatible versions.
5. Verify jobs, RBAC, credentials references, plugin startup, Kubernetes cloud and a synthetic build.
6. Measure actual RTO/RPO, record gaps and preserve audit evidence.
7. Validate no two controllers mount the same writable home concurrently.

A PVC snapshot alone may not guarantee application-consistent recovery. Do not copy live mutable Jenkins files without a consistency strategy.

## 11. Capacity and cost model

Calculate `agent CPU request × concurrent Pods`, memory/ephemeral-storage demand, node allocatable resources, warm capacity and burst scale-up time. Include EKS/AKS control-plane charges, worker VMs, EBS/managed disks, Azure Disk, network egress/NAT, log ingestion, artifact storage, registry and Spot interruption overhead. Optimize requests based on measured p95 rather than blanket downsizing.

## 12. Troubleshooting decision tree

```text
Jenkins build stuck or failed?
 ├─ Controller unavailable → probes/PVC/backup
 ├─ No agent provisioned → cloud API/RBAC/plugin
 ├─ Pod Pending → quota/taints/affinity/node capacity
 ├─ Image pull fails → registry IAM/ACR/ECR/DNS
 ├─ Pod running, no connection → inbound agent/remoting/TLS
 ├─ Build OOM/Evicted → requests/limits/node pressure
 ├─ AWS/Azure API denied → workload identity/federation/RBAC
 ├─ Autoscaler stalled → pool constraints/quota/capacity
 └─ Artifacts missing → workspace lifecycle/retention
```

## 13. Production runbooks

### A. New cluster onboarding
1. Review architecture, identity boundaries and capacity model.
2. Install/configure supported controller and Kubernetes plugin versions.
3. Provision namespace, RBAC, service accounts, quotas and Pod templates.
4. Verify agent build, cloud identity positive/negative tests and cleanup.
5. Exercise alerts, backups, restore and game-day acceptance.

### B. Agent provisioning outage
1. Capture Jenkins queue, cloud plugin logs and Kubernetes events.
2. Distinguish RBAC, scheduler, image pull, remoting and autoscaler.
3. Restore only affected control without broadening credentials.
4. Validate fresh agent and queue drain.
5. Record SLO impact and corrective action.

### C. Cloud identity incident
1. Quarantine affected workload and capture principal/SA/issuer.
2. Audit IAM/Azure RBAC and projected token injection.
3. Revoke exposed credentials or incorrect federation bindings.
4. Restore exact scoped identity and verify unauthorized action denied.
5. Preserve security evidence and review blast radius.

### D. Controller outage/restore
1. Stop conflicting writers and preserve incident logs.
2. Identify last consistent backup and compatible software versions.
3. Restore into isolated controller, validate integrity.
4. Reconnect Kubernetes cloud, test synthetic Pipeline.
5. Confirm RTO/RPO and resume controlled workloads.

### E. Cost or capacity regression
1. Compare queue p95, Pod startup, requests/limits and cloud cost.
2. Identify node pool overprovisioning, cold pulls or telemetry growth.
3. Tune quotas, template sizing and autoscaler policy.
4. Verify reliability before/after and cost change.
5. Record approval and monitoring thresholds.

## 14. 100-point enterprise acceptance

| Domain | Points |
|---|---:|
| Architecture, ownership and trust boundaries | 10 |
| Controller persistence, backup and restore | 15 |
| Kubernetes RBAC, Pod templates and security | 15 |
| EKS IAM/IRSA/Pod Identity validation | 10 |
| AKS Entra Workload ID and Azure RBAC validation | 10 |
| Autoscaling, node pools and capacity | 10 |
| Observability and SLOs | 10 |
| Failure injection and incident response | 15 |
| FinOps and evidence handover | 5 |
| **Total** | **100** |

Suggested pass: **85/100** plus mandatory gates: no exposed static cloud credentials, build SA cannot manage Secrets/Pods, unauthorized AWS/Azure access denied where tested, synthetic dynamic agent succeeds, restore tested, and all critical recovery gaps documented. If a cloud is unavailable, score that section as not tested and **do not claim full multi-cloud acceptance**.

## 15. Final handover package

Architecture/RACI, chart/JCasC/plugin versions, generated Pod specs, provisioner RBAC, AWS/Azure federation evidence, SLO dashboards, autoscaler/node pool metrics, 20 fault drills, backup/restore evidence, cost baseline, scorecard, risks and owner sign-off.

**Companion:** [Chapter 050 capstone lab](labs/050-jenkins-kubernetes-eks-aks-production-operations-capstone-check.md).  
**Part 10 complete:** Chapters 046–050.  
**Next:** Chapter 051 — Jenkins Helm-Based Kubernetes Deployments and Release Automation, beginning Part 11.
