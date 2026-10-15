# Chapter 076 — Google Kubernetes Engine GitOps Architecture, Cluster Provisioning and Platform Foundations

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 16:** Google Kubernetes Engine (GKE)  
**Chapter:** 076 / 100  
**Audience:** Platform Engineers, SREs, DBREs, DevSecOps and Cloud Architects

> **Safety:** All commands and labs target a dedicated, budget-controlled staging Google Cloud project with synthetic workloads. GKE, Cloud NAT, private connectivity, logging and VM nodes may incur charges. Never delete a production cluster, alter shared VPC routes, or expose a private control plane to troubleshoot access. Confirm the active project and kubectl context before writes.

## 1. Learning objectives

After this chapter you will:

1. Explain GKE control-plane and node responsibility boundaries.
2. Compare GKE Standard and Autopilot operational models.
3. Design regional clusters, private nodes, control-plane access and VPC-native networking.
4. Provision a reviewed GKE foundation with Terraform.
5. Configure IAM, Kubernetes RBAC and Workload Identity Federation for GKE.
6. Connect Artifact Registry with scoped node/workload identities.
7. Bootstrap Argo CD and GitLab CI/CD without static privileged kubeconfigs.
8. Configure observability, backup, upgrade and DR foundations.
9. Troubleshoot GKE provisioning, networking, identity and image-pull failures.
10. Complete enterprise operational acceptance.

## 2. Reference architecture

~~~text
Google Cloud Organization / IAM / Org Policy
                    |
          Folder / staging project
                    |
      GitLab protected Terraform MR
                    |
      VPC / subnets / secondary ranges
                    |
     Cloud NAT / Cloud DNS / firewall
                    |
          GKE regional cluster
         private nodes / control plane
                /         \
         system pool     user pools
             |              |
           Argo CD      applications
             |              |
        GitOps sync      GKE WIF
             |              |
         Kubernetes RBAC  Google APIs
                \         /
             Artifact Registry
                    |
          Ingress / Gateway / TLS
                    |
       Persistent Disk CSI / Filestore
                    |
     Cloud Logging / Monitoring / Managed Prometheus
                    |
          SRE alerts and DR plans
~~~

**Ownership:** Terraform manages GCP resources, cluster settings and node pools. Argo CD owns delegated Kubernetes resources. GKE owns the managed control plane and supported managed controllers. Never assign overlapping Terraform and Argo CD ownership of the same Kubernetes object.

## 3. GKE Standard versus Autopilot

| Dimension | Standard | Autopilot |
| --- | --- | --- |
| Node administration | User manages node pools | GKE manages node provisioning |
| Capacity control | Cluster autoscaler/node pools | Autopilot workload-driven provisioning |
| Workload constraints | Broad supported configuration | Autopilot admission and workload rules |
| Billing | Cluster/node resources and services | Autopilot-specific pricing model |
| Platform add-ons | Greater node-level flexibility | Must satisfy Autopilot restrictions |
| Typical choice | Detailed SRE node control | Reduced node-management burden |

Choose based on workload compatibility, security controls, cost and operational responsibilities. This chapter's Terraform and node-pool labs focus on **GKE Standard**. Autopilot requires its own supported configuration and should not be treated as a drop-in equivalent.

## 4. GKE regional architecture

Prefer a regional cluster for critical environments where supported and justified by cost. A regional control plane offers stronger availability than a single-zone control-plane design; application availability still requires resilient node pools, replicas and zone-aware storage.

Validate regional VM quota, zones, network ranges and disaster recovery dependencies. Regional does not automatically mean multi-region DR.

## 5. Prerequisites

- Google Cloud project with billing, quotas and approved IAM.
- Organization policies and VPC design approved.
- gcloud, gke-gcloud-auth-plugin, Terraform, kubectl and Helm installed.
- GitLab protected repository and approved CI identity federation.
- Argo CD bootstrap and AppProject governance.
- Artifact Registry repository, signing and scanning workflow.
- Private control-plane connectivity and Cloud DNS design.
- Cloud Logging, Monitoring and cost budget plan.

~~~bash
gcloud auth login
gcloud config get-value project
gcloud projects describe PROJECT_ID
gcloud services list --enabled --project PROJECT_ID
gcloud version
terraform version
kubectl version --client
~~~

Stop if the project, organization, region or cluster differs from the approved change.

## 6. Google Cloud APIs and quotas

Required services vary with architecture, but commonly include Kubernetes Engine, Compute Engine, IAM, Artifact Registry, Cloud Logging, Cloud Monitoring and Service Usage.

~~~bash
gcloud services enable \
  container.googleapis.com \
  compute.googleapis.com \
  iam.googleapis.com \
  artifactregistry.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  --project PROJECT_ID
~~~

Enabling APIs is a project-level change and requires appropriate authorization. Review quota and billing before provisioning.

## 7. VPC-native networking

GKE VPC-native clusters use alias IP ranges. Plan a primary subnet range for nodes and secondary ranges for Pods and Services.

~~~text
VPC:                  vpc-gke-staging
Subnet primary:       10.50.0.0/20
Pod secondary:        10.60.0.0/16
Service secondary:    10.70.0.0/20
Private services:     dedicated ranges as required
~~~

Ranges are illustrative. Validate overlap with on-premises, peered VPCs, Cloud VPN, Interconnect and recovery regions. Understand GKE IP allocation per node and expected max Pods before selecting secondary ranges.

## 8. Private nodes and control-plane access

Private nodes lack external IPs. Their outbound access to required APIs, registries and approved destinations may rely on Private Google Access, Cloud NAT, firewall rules and DNS.

GKE control-plane access modes and supported private endpoint options vary by cluster configuration and release. Use the currently supported private endpoint/DNS-based access method and authorized management networks. A private node cluster does not automatically imply that every control-plane endpoint is private.

## 9. Cloud NAT and egress

Cloud NAT can provide outbound connectivity for private nodes without public node IPs. Design NAT port capacity, firewall policies, egress logging and cost controls.

Do not assume Cloud NAT is needed for every Google API endpoint; Private Google Access and supported private endpoint patterns may satisfy some access paths. Verify actual traffic and DNS before introducing NAT.

## 10. Firewall rules and DNS

Restrict ingress to approved load balancers, health checks and management paths. Avoid blanket ingress rules. Use Cloud DNS private zones where appropriate and test Kubernetes DNS resolution independently from VPC DNS.

Private API access must be tested from the operator network or approved GitLab runner before a change window.

## 11. Terraform layout

~~~text
gke-foundations/
  terraform/
    versions.tf
    providers.tf
    variables.tf
    project-services.tf
    network.tf
    identities.tf
    gke.tf
    nodepools.tf
    observability.tf
    outputs.tf
    environments/staging.tfvars
  gitops/
    bootstrap/argocd/
    clusters/gke-staging/
      platform/
      applications/
  ci/
    validate-terraform.sh
    validate-manifests.sh
    verify-artifacts.sh
  runbooks/
    cluster-access.md
    workload-identity.md
    network-egress.md
    nodepool-recovery.md
~~~

Use a secure remote Terraform backend such as a dedicated GCS bucket with versioning, encryption, access controls and locking behavior validated for your Terraform version. Never commit state or sensitive plan artifacts.

## 12. Terraform providers and variables

~~~hcl
terraform {
  required_version = ">= 1.7.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" { type = string }
variable "region" { type = string }
variable "cluster_name" { type = string }
~~~

Pin exact provider versions and validate current resource schemas before production. The provider constraint is illustrative, not a guarantee of compatibility with every GKE feature.

## 13. Terraform VPC and subnet

~~~hcl
resource "google_compute_network" "gke" {
  name                    = "vpc-gke-staging"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "nodes" {
  name          = "snet-gke-staging"
  region        = var.region
  network       = google_compute_network.gke.id
  ip_cidr_range = "10.50.0.0/20"

  secondary_ip_range {
    range_name    = "gke-pods"
    ip_cidr_range = "10.60.0.0/16"
  }

  secondary_ip_range {
    range_name    = "gke-services"
    ip_cidr_range = "10.70.0.0/20"
  }

  private_ip_google_access = true
}
~~~

Add reviewed firewall, routes, NAT and DNS resources to the complete module. This fragment alone is not a hardened landing zone.

## 14. Terraform GKE Standard regional cluster

~~~hcl
resource "google_container_cluster" "gke" {
  name     = var.cluster_name
  location = var.region

  network    = google_compute_network.gke.id
  subnetwork = google_compute_subnetwork.nodes.id

  networking_mode = "VPC_NATIVE"

  ip_allocation_policy {
    cluster_secondary_range_name  = "gke-pods"
    services_secondary_range_name = "gke-services"
  }

  private_cluster_config {
    enable_private_nodes = true
  }

  workload_identity_config {
    workload_pool = "PROJECT_ID.svc.id.goog"
  }

  release_channel {
    channel = "REGULAR"
  }

  remove_default_node_pool = true
  initial_node_count       = 1

  deletion_protection = true
}
~~~

Replace PROJECT_ID with the real project identifier before deployment. This is an instructional fragment: choose a supported control-plane access mode, network policy/dataplane, logging, monitoring, maintenance, authorized networks and security settings before apply. Some configurations require additional arguments depending on provider/GKE release. Validate regional initial node behavior and quota.

## 15. Terraform node pool

~~~hcl
resource "google_container_node_pool" "apps" {
  name       = "apps"
  location   = var.region
  cluster    = google_container_cluster.gke.name
  node_count = 1

  autoscaling {
    min_node_count = 1
    max_node_count = 4
  }

  node_config {
    machine_type = "e2-standard-4"
    service_account = google_service_account.nodes.email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    labels = {
      workload_tier = "applications"
    }
    metadata = {
      disable-legacy-endpoints = "true"
    }
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}
~~~

This assumes a separately declared least-privilege node service account. OAuth scopes do not grant IAM permissions by themselves. In regional clusters, node_count semantics may apply per zone; review total VM count and cost carefully. Do not allow Terraform to fight autoscaler-managed desired size.

## 16. GKE node service account

~~~hcl
resource "google_service_account" "nodes" {
  account_id   = "gke-staging-nodes"
  display_name = "GKE staging node identity"
}
~~~

Grant only required roles for node operation, telemetry and Artifact Registry pulls. Google Cloud IAM roles, GKE workload identities and Kubernetes RBAC are separate trust boundaries.

## 17. Workload Identity Federation for GKE

Workload Identity Federation for GKE allows Kubernetes ServiceAccounts to access Google Cloud APIs without exporting long-lived service account keys. Supported identity principal forms and optional Kubernetes-to-IAM service account linking patterns vary by use case.

Prefer direct resource IAM grants to the Kubernetes workload principal where supported. When using IAM service account impersonation, configure the approved annotation and principal binding precisely.

## 18. Workload ServiceAccount example

~~~yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: demo-reader
  namespace: demo-staging
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-reader
  namespace: demo-staging
spec:
  replicas: 2
  selector:
    matchLabels:
      app: demo-reader
  template:
    metadata:
      labels:
        app: demo-reader
    spec:
      serviceAccountName: demo-reader
      containers:
        - name: app
          image: REGION-docker.pkg.dev/PROJECT_ID/demo/app@sha256:REPLACE_WITH_REAL_DIGEST
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              memory: 256Mi
~~~

Replace registry, project and digest placeholders. Grant the exact workload principal minimum IAM permissions to its target resource; no static service account key is required.

## 19. Kubernetes authentication and authorization

~~~bash
gcloud container clusters get-credentials gke-staging \
  --region REGION --project PROJECT_ID
kubectl config current-context
kubectl auth can-i list pods -n demo-staging
kubectl auth can-i get secrets -n demo-staging
~~~

The gke-gcloud-auth-plugin must be available. Authentication success does not imply authorization. Apply least-privilege Kubernetes RoleBindings and review GKE IAM permissions.

## 20. Artifact Registry integration

Use Artifact Registry repositories with restricted writer identities and approved pull permissions for nodes. Deploy immutable digests, scan images and enforce signed artifacts through a supported admission control mechanism.

~~~bash
gcloud artifacts repositories list --location REGION --project PROJECT_ID
gcloud container clusters describe gke-staging \
  --region REGION --project PROJECT_ID \
  --format="value(workloadIdentityConfig.workloadPool)"
kubectl -n demo-staging get pods
~~~

Never embed Artifact Registry credentials in Git. Distinguish node image-pull identity from the application workload identity used for Google APIs.

## 21. Argo CD bootstrap

Install a pinned Argo CD release through an approved bootstrap process, configure SSO, restricted AppProjects and trusted repositories, and place controllers on stable capacity.

~~~text
Terraform -> VPC / GKE / IAM / node pools
      |
Approved bootstrap -> Argo CD
      |
Platform AppProject -> policy, ingress, CSI, observability
      |
Application AppProjects -> workloads and namespaces
      |
GitLab CI -> verified digest -> protected GitOps MR
      |
Argo CD -> desired Kubernetes state
~~~

Avoid Terraform and Argo CD managing the same Kubernetes resources.

## 22. GitLab CI example

~~~yaml
stages: [validate, policy, plan]

terraform_validate:
  stage: validate
  image: registry.example.internal/ci/terraform-gcp:PINNED_DIGEST
  script:
    - terraform -chdir=terraform fmt -check
    - terraform -chdir=terraform init -backend=false
    - terraform -chdir=terraform validate

policy:
  stage: policy
  image: registry.example.internal/ci/policy-tools:PINNED_DIGEST
  script:
    - ./ci/check-gke-security.sh
    - ./ci/check-gke-networking.sh

plan:
  stage: plan
  image: registry.example.internal/ci/terraform-gcp:PINNED_DIGEST
  script:
    - ./ci/create-reviewed-plan.sh
~~~

Internal images/scripts are placeholders. Use GitLab-to-Google Cloud Workload Identity Federation for short-lived CI access where supported; protect plan artifacts and require independent apply approval.

## 23. GKE security baseline

- Organization Policy and project isolation.
- Private nodes and approved control-plane endpoint access.
- Least-privilege Google Cloud IAM and Kubernetes RBAC.
- Workload Identity Federation for GKE.
- Shielded GKE Nodes where supported.
- NetworkPolicy enforcement and restricted egress.
- Pod Security Admission and approved policy controller.
- Artifact Registry scanning and signed image admission.
- Secret Manager/CSI or approved external secret delivery.
- Audit logs and protected GitOps repositories.

Feature availability differs between Standard and Autopilot. Test admission policy against platform add-ons before enforcement.

## 24. Observability and upgrades

Configure Cloud Logging, Cloud Monitoring, Managed Service for Prometheus and SRE dashboards. Monitor node readiness, unschedulable Pods, DNS, ingress, persistent storage, workload identity, Argo CD reconciliation and cost.

Select a GKE release channel and maintenance windows. Review supported Kubernetes versions, node image compatibility, deprecated APIs and backup/restore before upgrades. Do not assume control-plane downgrades are a standard recovery mechanism.

## 25. Lab A — GCP project and IAM preflight

1. Verify organization, project, billing and region.
2. Inspect enabled APIs and quota.
3. Review project IAM and Organization Policy.
4. Verify approved cost budget and labels.
5. Confirm network ownership.
6. Save redacted evidence.

**Pass:** staging changes are limited to approved project.

## 26. Lab B — Terraform VPC foundation

1. Create custom VPC and node subnet.
2. Define secondary Pod and Service ranges.
3. Validate no overlap with connected networks.
4. Review firewall and Cloud NAT plan.
5. Run Terraform plan and protected approval.
6. Verify created network.

**Pass:** VPC-native networking is repeatable.

## 27. Lab C — Regional GKE Standard cluster

1. Pin Terraform provider and approved GKE release channel.
2. Provision regional private-node GKE cluster.
3. Configure workload pool and approved endpoint access.
4. Verify control-plane status.
5. Verify node pools and zone placement.
6. Record baseline.

**Pass:** cluster is healthy and securely accessible.

## 28. Lab D — Private node egress

1. Inspect node external IPs.
2. Validate Private Google Access.
3. Test approved Google API and Artifact Registry access.
4. Simulate restricted egress in isolated test.
5. Inspect NAT/firewall/DNS.
6. Restore required connectivity.

**Pass:** private nodes function without broad public ingress.

## 29. Lab E — GKE authentication and RBAC

1. Install gke-gcloud-auth-plugin.
2. Obtain cluster credentials.
3. Verify read-only namespace access.
4. Attempt unauthorized Secret read.
5. Confirm denial and audit.
6. Revoke temporary test access.

**Pass:** authentication and authorization are separate.

## 30. Lab F — Workload Identity Federation

1. Create synthetic Kubernetes ServiceAccount.
2. Grant scoped Google API permission to exact workload principal.
3. Deploy synthetic workload.
4. Test authorized read.
5. Test denied write and unrelated ServiceAccount.
6. Remove test permission.

**Pass:** no service account key file is required.

## 31. Lab G — Artifact Registry pull

1. Create private staging repository.
2. Grant node identity required pull permission.
3. Push synthetic digest-pinned image.
4. Deploy it to GKE.
5. Revoke disposable test pull permission.
6. Restore scoped permission and verify recovery.

**Pass:** image pull is identity-controlled.

## 32. Lab H — Node pool placement

1. Create separate user pool.
2. Apply workload node selectors.
3. Verify placement and AZ distribution.
4. Introduce invalid selector in test namespace.
5. Observe Pending scheduler event.
6. Restore valid placement.

**Pass:** scheduling constraints are diagnosable.

## 33. Lab I — Cluster Autoscaler

1. Configure safe autoscaling bounds.
2. Deploy synthetic workload with CPU requests.
3. Scale replicas beyond current capacity.
4. Observe autoscaler events and new nodes.
5. Reduce replicas.
6. Verify scale-down and cost.

**Pass:** scaling operates within approved bounds.

## 34. Lab J — DNS and Service connectivity

1. Deploy synthetic API and Service.
2. Verify EndpointSlices and CoreDNS.
3. Resolve internal DNS from test Pod.
4. Test inter-namespace access.
5. Simulate wrong Service name.
6. Restore and record evidence.

**Pass:** service discovery is reliable.

## 35. Lab K — Ingress and TLS

1. Install approved GKE ingress/Gateway controller.
2. Deploy internal synthetic endpoint.
3. Configure test DNS and TLS.
4. Verify backend health.
5. Simulate wrong backend selector.
6. Restore healthy routing.

**Pass:** ingress is private where required and functional.

## 36. Lab L — Persistent storage baseline

1. Verify Persistent Disk CSI driver.
2. Create disposable StorageClass and PVC.
3. Deploy synthetic stateful Pod.
4. Write test data and checksum.
5. Restart Pod and verify integrity.
6. Document topology and reclaim behavior.

**Pass:** storage survives Pod restart.

## 37. Lab M — Argo CD bootstrap

1. Install pinned Argo CD release.
2. Configure SSO and restricted AppProjects.
3. Register approved GitOps repository.
4. Sync synthetic application.
5. Test denied cluster-scoped resource.
6. Capture revision and health evidence.

**Pass:** GitOps scope is enforced.

## 38. Lab N — GitLab protected promotion

1. Build and test synthetic image.
2. Generate SBOM, scan and sign digest.
3. Propose GitOps MR.
4. Obtain CODEOWNERS approval.
5. Verify Argo CD reconciliation.
6. Revert via reviewed MR.

**Pass:** promotion and rollback are traceable.

## 39. Lab O — Monitoring and incident response

1. Enable approved Cloud Logging and Monitoring.
2. Validate node/Pod metrics and audit events.
3. Trigger synthetic Pod failure.
4. Confirm alert delivery and runbook link.
5. Restore application.
6. Measure detection and recovery.

**Pass:** operational events are observable.

## 40. Troubleshooting — eighteen scenarios

| # | Symptom | Likely cause | Safe remediation |
| --- | --- | --- | --- |
| 1 | GKE creation fails | API/quota/IAM | Inspect GCP operation |
| 2 | VPC secondary range conflict | CIDR overlap | Correct approved ranges |
| 3 | Private endpoint unreachable | DNS/network | Restore authorized path |
| 4 | gcloud auth plugin fails | Missing plugin/identity | Repair client auth |
| 5 | kubectl Forbidden | Kubernetes RBAC | Restore scoped access |
| 6 | Nodes cannot pull images | Artifact Registry IAM/egress | Repair pull path |
| 7 | Private nodes lack egress | NAT/Private Google Access | Fix approved egress |
| 8 | Workload API denied | WIF principal IAM | Correct resource role |
| 9 | Workload uses wrong identity | KSA/annotation/config | Repair trust |
| 10 | Pods Pending | Affinity/taints/resources | Inspect scheduler |
| 11 | Autoscaler not scaling | Quota/limits/constraints | Restore capacity |
| 12 | CoreDNS failures | Upstream/network | Restore DNS |
| 13 | Ingress backend unhealthy | Selector/health checks | Restore endpoints |
| 14 | PVC Pending | CSI/topology | Inspect provisioning |
| 15 | Admission denies workload | Pod policy | Fix compliant manifest |
| 16 | Argo CD OutOfSync | Drift/permission | Reconcile Git |
| 17 | Audit logs missing | Logging configuration | Restore collection |
| 18 | Upgrade stalls | PDB/API compatibility | Restore headroom |

## 41. Runbook — GKE cluster provisioning failure

1. Verify project, region, APIs and billing.
2. Inspect Terraform plan and GCP operation.
3. Check IAM, quotas and VPC secondary ranges.
4. Validate private endpoint and node service account.
5. Repair approved dependencies.
6. Reapply reviewed plan.
7. Document RCA and cost.

## 42. Runbook — private control-plane connectivity outage

1. Confirm GKE cluster status in Google Cloud.
2. Verify operator identity and auth plugin.
3. Inspect endpoint access mode, DNS and routes.
4. Test from approved management network.
5. Restore private access without broad public exposure.
6. Validate kubectl and Argo CD.
7. Record evidence.

## 43. Runbook — Workload Identity Federation incident

1. Identify Kubernetes ServiceAccount and workload principal.
2. Review workload pool, annotations if used and IAM bindings.
3. Inspect Google API authorization and audit logs.
4. Restore exact principal trust and scoped permissions.
5. Test allowed and denied operations.
6. Remove obsolete keys and permissions.
7. Document preventive checks.

## 44. Runbook — node pool or networking incident

1. Identify affected nodes, AZs and workloads.
2. Inspect scheduler, autoscaler and quota.
3. Review Pod/Service secondary ranges and firewall.
4. Validate private node egress and Artifact Registry.
5. Restore approved node/network capacity.
6. Confirm SLO and data integrity.
7. Update capacity forecast.

## 45. Runbook — GitOps bootstrap recovery

1. Confirm GKE cluster and system capacity.
2. Restore pinned Argo CD controllers and CRDs.
3. Reapply approved repositories and AppProjects.
4. Reconcile platform components before apps.
5. Verify Workload Identity, ingress and storage.
6. Confirm Git revision and SLO.
7. Archive incident evidence.

## 46. Evidence template

~~~text
Change / lab ID:
GCP organization, project, region and cluster:
Terraform state, plan and version:
GKE mode, release channel and Kubernetes version:
VPC, node subnet, Pod/Service secondary ranges:
Private endpoint, DNS and egress:
Node pools, AZs, quota and autoscaling:
Google IAM and Kubernetes RBAC:
Workload Identity Federation principal:
Artifact Registry repository and image digest:
GitLab pipeline and GitOps MR:
Argo CD project, revision and health:
Cloud Logging/Monitoring evidence:
Persistent storage and backup:
SLO, recovery time and budget:
Owner and reviewer:
~~~

## 47. Scored operational readiness

| Domain | Points | Evidence |
| --- | ---: | --- |
| GCP project, IAM and Terraform | 20 | Approved IaC and roles |
| Regional GKE and node pools | 20 | Healthy nodes, autoscaling |
| VPC-native network and private access | 20 | CIDR, DNS and egress tests |
| Workload identity and Artifact Registry | 15 | Allowed/denied access |
| GitLab and Argo CD governance | 10 | Protected promotion/rollback |
| Observability and recovery | 10 | Alerts and runbooks |
| FinOps and documentation | 5 | Budget and evidence |
| **Total** | **100** | |

**Pass:** at least 85/100 with no critical failure: wrong project, unauthorized public API exposure, unscoped privileged access, static service account keys in workloads, unreviewed GitOps promotion or missing cluster recovery plan.

## 48. Final acceptance checklist

- [ ] Approved project, region, APIs and budget confirmed.
- [ ] Terraform state secured and plan reviewed.
- [ ] GKE Standard versus Autopilot choice documented.
- [ ] Regional availability and node pools validated.
- [ ] VPC-native secondary ranges nonoverlapping.
- [ ] Private endpoint access and node egress tested.
- [ ] Google IAM and Kubernetes RBAC scoped.
- [ ] Workload Identity Federation positive/negative tests passed.
- [ ] Artifact Registry pull and signed digest verified.
- [ ] Argo CD AppProjects and GitLab MR protections tested.
- [ ] Persistent storage and backup approach reviewed.
- [ ] Cloud Logging/Monitoring and alerts operational.
- [ ] Fifteen hands-on labs completed.
- [ ] Eighteen troubleshooting scenarios reviewed.
- [ ] Five production runbooks validated.
- [ ] Evidence and operational owners accepted.

## 49. Knowledge check

1. What are the operational differences between GKE Standard and Autopilot?
2. Why are Pod and Service secondary IP ranges necessary in VPC-native GKE?
3. Why do private nodes require explicit egress planning?
4. How do Google IAM and Kubernetes RBAC differ?
5. What does Workload Identity Federation for GKE replace?
6. Why is Artifact Registry pull identity distinct from workload identity?
7. Why does a regional cluster not guarantee multi-region DR?
8. How should Terraform and Argo CD resource ownership be divided?
9. What can block GKE node autoscaling?
10. Which evidence demonstrates production readiness?

## 50. References

- [Google Kubernetes Engine documentation](https://cloud.google.com/kubernetes-engine/docs)
- [GKE cluster architecture](https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-architecture)
- [GKE Autopilot overview](https://cloud.google.com/kubernetes-engine/docs/concepts/autopilot-overview)
- [GKE VPC-native networking](https://cloud.google.com/kubernetes-engine/docs/concepts/alias-ips)
- [GKE private nodes](https://cloud.google.com/kubernetes-engine/docs/how-to/private-clusters)
- [Workload Identity Federation for GKE](https://cloud.google.com/kubernetes-engine/docs/concepts/workload-identity)
- [GKE IAM](https://cloud.google.com/kubernetes-engine/docs/concepts/access-control)
- [GKE Cluster Autoscaler](https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-autoscaler)
- [Artifact Registry](https://cloud.google.com/artifact-registry/docs)
- [GKE Observability](https://cloud.google.com/kubernetes-engine/docs/concepts/observability)
- [Terraform Google Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Argo CD](https://argo-cd.readthedocs.io/en/stable/)
- [GitLab CI/CD](https://docs.gitlab.com/ci/)

---

**Chapter 076 complete — Part 16: Google Kubernetes Engine started.**

**Next:** Chapter 077 — GKE Node Pools, Autoscaling, Scheduling and Production Capacity Management.