# Chapter 044 — Azure Compute, AKS and Application Infrastructure with Terraform

**Part 09 — Azure Infrastructure as Code · Chapter 044 of 120**  
**Audience:** Platform SRE, DBRE, Cloud Engineering, DevSecOps  
**Prerequisites:** Chapters 041–043; Terraform >=1.7, Python >=3.9; Azure CLI and approved subscription only for optional integration.

> **Safety boundary:** All required exercises are executable offline using Terraform's built-in \`terraform_data\` provider. The AzureRM reference configuration is review-only and must not be applied without network, identity, quota, budget, and change approvals.

## 1. Learning outcomes

Design an enterprise Azure application platform integrating VMs, Virtual Machine Scale Sets (VMSS), Azure Kubernetes Service (AKS), Application Gateway and ingress, Azure Container Registry (ACR), managed identities, workload identity, private networking, autoscaling, diagnostics and resilient deployment. Develop IaC controls that reject unreviewed production changes, test SRE/DBRE failure scenarios, and create an auditable operational handoff.

## 2. Reference architecture

~~~text
                 Clients / approved private ingress
                              |
               WAF / Application Gateway (TLS)
                              |
                 Private AKS cluster endpoint
                     |                 |
             System node pool     User node pools
             critical addons     apps + HPA/KEDA
                     |                 |
                     +----- Services --+
                              |
                    Workload Identity
                              |
               Key Vault / ACR / Azure Monitor
                              |
             Private endpoints and Private DNS
                              |
                Azure PostgreSQL / SQL / Redis

     Parallel VM / VMSS tier for legacy or specialized apps
         Azure Load Balancer -> VMSS -> managed disks
~~~

**Control plane versus data plane:** AKS manages Kubernetes control-plane infrastructure; customers remain responsible for node pools, application security, pod disruption budgets, network policies, workloads, secrets and upgrade scheduling. A private AKS API endpoint needs appropriate private DNS and administrative connectivity. Managed identity alone does not grant Kubernetes RBAC or application data-plane permissions.

## 3. Azure compute design

### Virtual machines

Select SKU by vCPU, memory, local/remote storage throughput, architecture, zones, accelerated networking and quota. Prefer trusted launch and disk encryption when supported; use hardened images, managed disks, boot diagnostics, Azure Monitor Agent and Defender recommendations. Avoid public IPs and password authentication. Use Azure Bastion or an approved private access path.

### Virtual Machine Scale Sets

VMSS provides instance scaling and rolling upgrades, but readiness, health probes, image versions, fault domains and graceful termination must be configured explicitly. Separate autoscaling policies from application capacity limits. Scale-out cannot resolve a downstream database connection limit; coordinate concurrency and pool sizing with DBRE.

### Application Gateway, load balancers and ingress

Azure Load Balancer operates at L4; Application Gateway supports L7 routing and optional WAF. AKS ingress implementation choices vary by version and deployment model. Do not assume an ingress controller is installed automatically. Enforce end-to-end TLS, certificate rotation, health probes, client IP forwarding and WAF tuning.

## 4. AKS architecture and node pools

System pools host critical system workloads and must have sufficient capacity; user pools isolate applications by workload, architecture, taints and node selectors. Design zones, upgrade surge capacity, PodDisruptionBudgets, topology spread, resource requests/limits, cluster autoscaler boundaries and drain timeouts. Validate quota for temporary upgrade nodes.

AKS network models (Azure CNI Overlay and other supported choices) change IP planning and routing requirements. Confirm the chosen model against Chapter 042 subnet and Private DNS design. Protect Kubernetes API access with Microsoft Entra integration, Azure RBAC or Kubernetes RBAC as appropriate, private endpoint connectivity and auditable break-glass.

## 5. Identity, registry and secrets

Use kubelet identity for ACR image pulls and workload identity federation for pod access to Azure services. Bind service accounts to narrowly scoped identities and Key Vault permissions. Avoid embedding registry credentials, service-principal secrets or application passwords in Terraform state. CSI Secrets Store and external secret controllers require lifecycle, rotation and failure-mode design; they do not eliminate source-secret security obligations.

Pin images by digest, scan images, restrict registries and use admission policy. Configure image pull fallback behavior and rollout protections. Treat GitOps drift and Terraform ownership separately: Terraform should not fight application controllers for the same Kubernetes fields.

## 6. Capacity, availability and SLOs

- **Availability:** zones, node pool diversity, pod replicas, PDBs, graceful termination, ingress health and data-tier dependency failover.
- **Performance:** p95/p99 latency, CPU throttling, memory OOMs, disk latency, SNAT exhaustion, ingress queues and PostgreSQL connection saturation.
- **Scaling:** HPA/KEDA or VMSS autoscale, cluster autoscaler, min/max bounds, node provision time and application warm-up.
- **Cost:** node SKU, idle minimums, load balancers, managed disks, network egress, monitoring ingestion and AKS pricing tier.
- **Recovery:** backups and manifests are distinct from database PITR; Kubernetes redeployment does not restore lost persistent data.

Production acceptance needs load testing, upgrade simulation, zone disruption and verified recovery objectives.

## 7. Terraform module and state design

~~~text
iac/
  bootstrap/              # identity, remote state
  network/                # VNet, subnet, private DNS
  platform/
    modules/aks/
    modules/vmss/
    modules/identity/
    modules/monitoring/
  applications/           # separately owned delivery/GitOps
~~~

Pin AzureRM provider and Terraform versions, check the lockfile into source control, use per-environment state and secure Azure Blob backend. Separate cluster infrastructure from Kubernetes workload lifecycle when ownership differs. Never apply a saved plan generated against a different state or subscription. Use policy checks and a human review of every delete/replace action.

## 8. Executable hands-on labs

The accompanying directory is \`infrastructure-as-code/labs/chapter-044/\`.

### Lab A — Offline Terraform platform contract

~~~bash
cd infrastructure-as-code/labs/chapter-044
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter044.tfplan
terraform apply chapter044.tfplan
terraform output -json
terraform state list
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "plan_exit=$?"
~~~

Four \`terraform_data\` resources model compute, AKS, application delivery and SRE observability. Production variables enforce stronger preconditions. These resources do **not** create Azure VMs or AKS clusters.

### Lab B — Security, availability and destructive-change gates

~~~bash
python3 compute_gate.py fixtures/compute-safe.json fixtures/plan-safe.json compute-policy.json
python3 compute_gate.py fixtures/compute-unsafe.json fixtures/plan-destructive.json compute-policy.json
python3 -m unittest -v test_compute_gate.py
bash run-preflight.sh
~~~

The safe manifest must pass and unsafe/destructive inputs must fail. The Python gate checks declared subscription isolation, private cluster API, approved SKU and Kubernetes version, zone spread, minimum replicas, image digest, workload identity, ACR controls, PDB, autoscaling, private database connectivity, logging and audit. It is a **manifest contract gate**, not a replacement for parsing the full Terraform JSON plan, querying AKS, or proving workload availability.

### Lab C — Optional AzureRM plan-only exercise

1. Confirm tenant/subscription, location, service quotas and budget.
2. Review \`examples/azurerm-compute-aks.tf.example\` in a **separate** approved root. Confirm AKS supported Kubernetes version in the selected region, API access, subnet permissions, ACR, workload identity and DNS.
3. Configure a secured remote backend and federated identity. Run \`terraform init\`, \`terraform validate\`, \`terraform plan\`; **do not apply automatically**.
4. Review replacement actions, node pool upgrade surge, autoscaler, private ingress, identities and operational cost.
5. After formal approval, deploy only in a sandbox; validate \`kubectl get nodes -o wide\`, node taints, workloads, ingress TLS, metrics and application database probes.

## 9. SRE/DBRE failure injection scenarios

| Failure | Detection | Response |
|---|---|---|
| AKS node pool upgrade stalls | node Ready, PDB and drain events | inspect disruption budget, quota, surge and failing pods |
| Zone outage | unavailable nodes and ingress errors | reschedule replicas across healthy zones, verify data tier |
| ACR pull denied | ImagePullBackOff | inspect kubelet identity, ACR RBAC and network |
| Workload identity mismatch | 401/403 to Key Vault | verify OIDC issuer, service account annotation and federated subject |
| Cluster autoscaler blocked | Pending pods, scale-up errors | inspect max nodes, subnet IPs and VM quota |
| VMSS rollout unhealthy | probe failures, capacity loss | pause rollout, restore known-good image |
| Application Gateway 502 | backend health and TLS errors | inspect probes, backend DNS and certificates |
| PostgreSQL connection storm | connection saturation, timeouts | cap app concurrency, tune pools with DBRE |
| Private AKS DNS failure | kubectl cannot reach API | restore private zone links and resolver path |
| Monitoring blind spot | absent telemetry | restore diagnostic settings and agent coverage |

## 10. Troubleshooting decision tree

**No deployment:** inspect Terraform plan, Azure Policy, provider registration, quota, permissions and private endpoint DNS. **Pods Pending:** check scheduler events, taints, node capacity, quotas, CNI IP allocation and cluster autoscaler. **Pods CrashLoopBackOff:** inspect readiness/liveness, secrets, resource limits and downstream DB. **Intermittent 5xx:** correlate ingress/backend health, deployment revision, autoscaling and database latency. **Private data service unavailable:** test DNS, network, managed identity and TLS independently. Never resolve a connectivity issue by exposing a database publicly.

Useful diagnostics:

~~~bash
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get events -A --sort-by=.lastTimestamp
kubectl describe pod -n YOUR_NAMESPACE YOUR_POD
kubectl top nodes
kubectl rollout status deployment/YOUR_DEPLOYMENT -n YOUR_NAMESPACE
az account show --query '{tenant:tenantId,subscription:id}' -o json
~~~

These commands require appropriate connectivity and credentials; they are not executed by the offline lab.

## 11. Production runbooks

**Deployment:** freeze source revision, verify identity and state lock, inspect plan, approve network/DBRE dependencies, deploy canary, observe p95/p99 latency, error rate, pod restarts, node readiness and DB pool saturation, then promote.

**AKS upgrade incident:** stop parallel upgrades, capture events and PDB violations, restore node capacity and known-good workloads, coordinate change rollback and test service availability.

**Identity outage:** inspect service-account federation, managed identity and ACR/Key Vault roles; repair narrowly scoped trust without adding static credentials.

**Database overload:** reduce HPA/KEDA concurrency, pause rollout, tune connection pooling, validate database replication/failover and track recovery to SLO.

**Regional or zonal outage:** invoke DR plan; assess available replicas, private DNS and data-tier failover. Do not claim RPO/RTO until tested with actual data.

**Unexpected Terraform replacement:** halt apply, preserve state and plan, assess service interruption, obtain change authority and execute a safe migration plan rather than deleting production nodes blindly.

## 12. 100-point final acceptance

| Area | Points |
|---|---:|
| VM/VMSS/AKS architecture and capacity | 20 |
| Identity, ACR, secrets and network security | 20 |
| High availability, autoscaling and upgrade safety | 20 |
| Terraform and Python positive/negative tests | 15 |
| SRE/DBRE incident drills and recovery | 15 |
| Monitoring, cost, approvals and audit | 10 |

Pass **>=85/100**, with zero critical failures (public production API, static credentials, unapproved destructive plan, no database connectivity verification, or untested production upgrade/rollback). Attach sanitized CI evidence, reviewed plan, cluster configuration, SLO dashboards, incident runbook results and DBRE sign-off.

## 13. Cleanup and review questions

~~~bash
terraform destroy -var-file=environments/dev.tfvars
terraform state list
~~~

This cleans only the offline contract resources. Explain the distinction between cluster autoscaler and HPA; system versus user pools; workload identity versus kubelet identity; ingress versus L4 load balancing; PDB versus replica count; Terraform state recovery versus PostgreSQL PITR.

**Next: Chapter 045 — Azure Stateful Data, Storage, Resilience and Production Operations Capstone.**
