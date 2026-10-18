# Chapter 049 — GCP Compute, GKE and Application Infrastructure with Terraform

**Part 10 — Google Cloud Platform | Chapter 049/120**  
**Audience:** SRE, DBRE, platform engineering, cloud security and application operations  
**Prerequisites:** Chapters 046–048, Terraform >=1.7, Python >=3.9, optional approved GCP sandbox.

> **Safety and scope:** Required labs use Terraform's built-in \`terraform_data\` provider only; no cloud credentials or billing. GCP examples are review-only, not a complete production deployment. A passing declared-control policy fixture is not proof of live GKE, Compute Engine, database or ingress security. Never apply example configurations to production without review and authorization.

## 1. Learning outcomes

Design Compute Engine instances and managed instance groups (MIGs), regional versus zonal capacity, instance templates, autoscaling, health checks, rolling updates, load balancers, private VMs, OS Login and Shielded VM. Design GKE Standard and Autopilot tradeoffs, private clusters, VPC-native alias IPs, node pools, Workload Identity Federation for GKE, RBAC, network policy, Pod Security Standards, workload autoscaling, maintenance windows and upgrade safety. Provision application infrastructure using Terraform with immutable artifacts, secure ingress, monitoring, SLOs, rollback and SRE/DBRE acceptance.

## 2. Reference architecture

~~~text
        CI/CD OIDC -> Workload Identity Federation -> Terraform
                                |
                     Approved GCP service account
                                |
              Shared VPC / service project boundary
                                |
            Cloud Load Balancing + Cloud Armor + TLS
                  /                         \
        Compute Engine MIG              GKE cluster
         regional instances          private nodes + pools
                  |                         |
             health checks             HPA / KEDA / CA
                  |                         |
              Cloud NAT              Workload Identity
                  \                         /
                   Private Cloud SQL / Redis
                              |
                  Cloud Monitoring / Logging
                              |
                     GCS protected state
~~~

Separate state and identities for foundation networking, compute, GKE control plane, node pools and application deployment. Avoid applying Kubernetes manifests before a healthy cluster and credentials exist; a separate \`kubernetes\`/Helm stage simplifies bootstrap and recovery.

## 3. Compute Engine and instance groups

Compute Engine VMs combine machine family/series, image, boot and data disks, metadata, service account, network interface, firewall rules and availability placement. Use hardened images, Shielded VM, OS Login, no default external IP, restricted metadata, least-privilege identity and patch management. Instance templates are immutable specifications used by MIGs; changes typically roll to a new template version. Regional MIGs distribute capacity across zones when supported; design target size, update policy, surge, max unavailable, autohealing health checks, connection draining and disruption budgets. Autoscaling signals include CPU, load-balancer serving capacity and Cloud Monitoring metrics. Spot VMs are interruptible and appropriate only for interruption-tolerant pools.

| Choice | Suitable use | SRE/DBRE tradeoff |
|---|---|---|
| Single VM | disposable lab or narrow legacy workload | single-zone failure risk |
| Zonal MIG | single-zone horizontally scaled service | zonal outage |
| Regional MIG | resilient stateless application | cross-zone cost and capacity |
| GKE Standard | granular node pool, daemon and scheduling control | upgrade and node management |
| GKE Autopilot | managed node operations with supported constraints | reduced node-level control |

## 4. GKE architecture

GKE control plane runs as a managed service. Standard clusters require explicit decisions for private node pools, control-plane endpoint exposure, authorized networks, master global access where applicable, VPC-native Pod/Service secondary ranges, node auto-provisioning and release channels. Private nodes still require egress design for Google APIs, Artifact Registry and external dependencies. Autopilot changes node-management and workload constraints; verify supported features, billing and release behavior before selection.

Use distinct system/application pools as appropriate, zone spreading, taints/tolerations, topology spread constraints, requests/limits, PDBs and graceful shutdown. Distinguish cluster autoscaler (node count), HPA (pod replicas), VPA (requests recommendations/changes), and KEDA (event-driven workloads); coordinate signals to prevent oscillation. GKE maintenance exclusions and windows are not a substitute for upgrade testing and rollback plans. Some control-plane upgrades cannot simply be rolled back.

## 5. Workload identity, secrets and supply chain

Prefer Workload Identity Federation for GKE and scoped Google service accounts, with explicit Kubernetes service account mappings or direct principal grants as supported. Avoid exporting static service account keys. Use Artifact Registry, image digest pinning, Binary Authorization where justified, vulnerability scanning, SBOM/provenance verification and admission controls. Use Secret Manager runtime integration; do not place secret payloads into Terraform state, ConfigMaps, pod annotations or CI logs. Configure Kubernetes RBAC, namespace isolation, network policy, Pod Security Standards and least-privilege containers.

## 6. Networking, ingress and application delivery

Choose external or internal Application Load Balancer, GKE Gateway API/Ingress, Cloud Armor, managed TLS certificates, Cloud DNS, health checks and backend policies based on the application. Confirm whether internal services must be private, where TLS terminates, and how traffic reaches the pods/VMs. Cloud NAT handles outbound translation, not inbound access. For database clients, test Cloud SQL private connectivity, DNS, TLS, IAM, connection pooling, NAT limits and maximum connections under HPA/MIG scaling.

## 7. Stateful dependencies and DBRE concerns

Prefer managed Cloud SQL/AlloyDB or approved stateful platform for databases rather than casually placing production PostgreSQL on ephemeral containers. Evaluate backup/PITR, HA, RPO/RTO, regional replication, storage IOPS, connection count, pooler sizing, failover and migration. For Redis/Memorystore, evaluate topology, network and failover. For GKE persistent volumes, understand CSI driver, disk zone affinity, snapshots, reclaim policy, StatefulSet ordering and data recovery. Terraform state does not back up application data.

## 8. Observability, SLOs and cost

Capture GKE control-plane/node/pod health, MIG autohealing, load-balancer latency and 5xx, Cloud NAT ports, DNS, CPU/memory saturation, restart/OOMKill, image pulls, cluster autoscaler events, Cloud SQL connections and latency. Use Cloud Logging, Cloud Monitoring, managed Prometheus/OpenTelemetry as appropriate. Define error-budget burn alerts, dashboards and synthetic probes. Budget for GKE management charges where applicable, VM/node SKUs, persistent disks, load balancers, NAT, logging ingestion and inter-zone/region egress.

## 9. Terraform module boundaries

~~~text
gcp-platform/
  foundations/             # projects, APIs, IAM, remote state
  network/                 # VPC, secondary ranges, NAT, DNS
  compute-mig/             # instance templates, MIG, health checks
  gke-cluster/             # control plane, private endpoints
  gke-node-pools/          # autoscaling, zones, upgrade policy
  application-ingress/     # LB/Gateway, TLS, Cloud Armor
  observability/           # metrics, logs, SLOs, budgets
  app-deployment/          # separate Kubernetes/Helm stage
~~~

Provider resources to review include \`google_compute_instance_template\`, \`google_compute_region_instance_group_manager\`, \`google_compute_region_autoscaler\`, \`google_container_cluster\`, \`google_container_node_pool\`, \`google_compute_health_check\`, \`google_compute_backend_service\`, \`google_compute_url_map\`, \`google_compute_target_https_proxy\`, \`google_compute_global_forwarding_rule\`, \`google_monitoring_alert_policy\`. Schema, features and version compatibility must be verified for the pinned provider.

## 10. Executable hands-on labs

### Lab A — Offline Terraform compute and GKE contracts

~~~bash
cd infrastructure-as-code/labs/chapter-049
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter049.tfplan
terraform apply chapter049.tfplan
terraform output -json
terraform state list
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
~~~

Four \`terraform_data\` resources model Compute/MIG, GKE, application ingress and operations. They do **not** deploy GCP resources. Production preconditions deny public nodes, static keys, missing private GKE controls, unsigned/unpinned images, absent PDB/observability or unapproved changes. Use separate state per environment.

### Lab B — Fail-closed security and change policy

~~~bash
python3 compute_gate.py fixtures/compute-safe.json fixtures/plan-safe.json compute-policy.json
python3 compute_gate.py fixtures/compute-unsafe.json fixtures/plan-destructive.json compute-policy.json
python3 -m unittest -v test_compute_gate.py
bash run-preflight.sh
~~~

Expected: safe passes, unsafe and delete/replace fail. The fixtures are intentionally simplified declared evidence and plan-action contracts, **not** a general Terraform JSON plan parser.

### Lab C — Optional reviewed GCP sandbox

1. Validate project ID/number, billing, APIs, quotas, service agents, WIF, VPC secondary ranges and organization policy.
2. Review \`examples/google-compute-gke.tf.example\` as a separate Terraform root; do not apply blindly.
3. Plan a private VM/instance template and a private-node GKE Standard cluster; verify exact provider version and GKE release availability.
4. Review identity, cost, quota, firewall, API endpoint access, node pool upgrade, logging and destruction/replacement actions.
5. With approvals, deploy only in a disposable project, test workload identity, private API access, image pulls, ingress, autoscaling, DB connectivity and rollback; capture evidence.

## 11. Production SRE/DBRE scenarios

| Incident | Symptom | Investigate | Recovery |
|---|---|---|---|
| VM/MIG unhealthy | 5xx and unhealthy backends | health checks, template, startup logs | rollback template, restore capacity |
| Regional VM quota exhausted | MIG scaling blocked | quota, SKU, zone capacity | rightsize/approved quota |
| GKE private endpoint inaccessible | kubectl timeout | authorized networks, DNS, routing | restore approved management path |
| GKE Pod IP exhaustion | Pending pods / CNI errors | subnet secondary ranges, density | expand via approved migration |
| ImagePullBackOff | app rollout blocked | Artifact Registry IAM, NAT, DNS | restore narrow access |
| Workload identity 403 | API access fails | token audience, KSA/GSA mapping | repair scoped trust |
| Node NotReady | availability drop | kubelet, disk, CNI, VM health | cordon/drain/recover safely |
| HPA ineffective | latency and CPU high | metrics server, requests, scaling limits | fix signals and capacity |
| PDB blocks upgrade | stuck node drain | PDB, replicas, disruption | safely restore headroom |
| Cloud SQL connections saturated | DB errors during scale-out | pool size, max connections | cap fan-out, pool, tune |
| Persistent disk zone mismatch | pod unschedulable | PV topology, node zones | migrate/restore data safely |
| Terraform cluster replacement | destructive plan | immutable fields/state drift | block apply, plan migration |

## 12. Troubleshooting commands

~~~bash
gcloud compute instances list --project=PROJECT_ID
gcloud compute instance-groups managed list --project=PROJECT_ID
gcloud container clusters list --project=PROJECT_ID
gcloud container node-pools list --cluster=CLUSTER --location=LOCATION --project=PROJECT_ID
gcloud compute health-checks list --project=PROJECT_ID
gcloud compute backend-services list --project=PROJECT_ID
gcloud monitoring dashboards list --project=PROJECT_ID
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get events -A --sort-by=.lastTimestamp
kubectl describe pod POD -n NAMESPACE
kubectl get hpa,pdb -A
terraform state list
~~~

Use approved credentials, cluster contexts and namespaces. Never infer production cluster safety from a successful \`kubectl get nodes\` alone.

## 13. Production runbooks

**Pre-change:** validate project, cluster location/version, WIF, quotas, private network, node pool capacity, PDBs, backup/DR, change ticket and reviewed Terraform plan. Deny cluster/node pool replacement without migration.

**MIG rollout regression:** pause rollout, inspect backend health, revert instance template version, validate 5xx/latency and connection draining.

**GKE upgrade blocked:** check PDBs, resource headroom, maintenance policy and drain errors; restore safe replica count, reattempt under approved window.

**Workload identity outage:** inspect OIDC/STS and KSA/GSA binding, Cloud Audit Logs and application token use; restore narrow trust, no static-key fallback.

**DB saturation:** coordinate DBRE, measure pool fan-out, rate-limit/reduce app replicas if necessary, repair connection pooling and test read/write.

**Region/zone outage:** fail over stateless workloads and restore data-plane dependencies using tested procedures; measure actual RPO/RTO and service SLO recovery.

**Security event:** freeze changes, isolate affected identity/workload, preserve audit evidence, rotate exposed credentials and validate restored access.

## 14. Acceptance rubric (100 points)

| Gate | Points |
|---|---:|
| Compute Engine/MIG and capacity architecture | 20 |
| GKE networking, identity, security and lifecycle | 20 |
| Ingress, applications and DBRE dependencies | 20 |
| Terraform labs and automated negative tests | 15 |
| SRE/DBRE incidents, recovery and rollback | 15 |
| Observability, SLOs, FinOps and approvals | 10 |

Pass >=85/100 with zero critical failures: public cluster/node access, static keys, unapproved destructive change, absent database recovery, missing PDB/health checks or security approval. Publication is not live acceptance.

## 15. Cleanup

~~~bash
terraform destroy -var-file=environments/dev.tfvars
~~~

Only destroy offline lab resources or explicitly disposable sandbox resources. Review: How do MIG autohealing and autoscaling differ? Why does HPA not guarantee node capacity? Why can private GKE fail image pulls? What is the DBRE risk when application replicas increase? Why are PDBs necessary during upgrades?

**Next proposed:** Chapter 050 — GCP Stateful Data, Storage, Resilience and Production Operations Capstone.
