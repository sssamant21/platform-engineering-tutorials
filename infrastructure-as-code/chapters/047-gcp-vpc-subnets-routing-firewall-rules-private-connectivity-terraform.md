# Chapter 047 — GCP VPC, Subnets, Routing, Firewall Rules and Private Connectivity with Terraform

**Part 10 — Google Cloud Platform | Chapter 047/120**  
**Audience:** Platform engineers, SREs, DBREs, network security, incident responders  
**Prerequisites:** Chapters 046, 026–035; Terraform >=1.7, Python >=3.9; approved GCP project for optional cloud work.

> **Execution boundary:** Required exercises use only built-in Terraform \`terraform_data\` resources and JSON policy fixtures; no cloud credentials or billable infrastructure required. \`examples/google-vpc.tf.example\` is **review-only**, not a complete production network. Live connectivity, packet traces, IAM and security acceptance remain pending.

## 1. Learning objectives

Explain GCP global VPCs and regional subnets, IPv4 allocation, dual-stack considerations, Shared VPC, peering, Private Service Connect (PSC), Private Google Access, Cloud NAT, Cloud Router, Cloud DNS, Cloud VPN, Interconnect, firewall rules/policies, hierarchical policies and route selection. Design secure GKE/Cloud SQL/VM access without indiscriminate internet exposure. Implement an offline Terraform network contract and fail-closed security gate, simulate network failures and prepare SRE/DBRE runbooks.

## 2. Enterprise network architecture

~~~text
GCP Organization / folders / policies
                |
        Shared VPC host project
                |
    Global custom-mode VPC (RFC1918)
       |                |                |
  us-central1       us-east4       Hybrid edge
  Subnet A          Subnet B       Cloud VPN/Interconnect
       |                |                |
 GKE private nodes  App VMs        Cloud Router / BGP
       |                |
   Cloud NAT       Private Google Access
       |                |
    Google APIs / Artifact Registry / Secret Manager
                |
      Private Service Connect / private services access
                |
     Cloud SQL / managed services / producer endpoints
                |
   Cloud DNS + Firewall Policies + Flow Logs + Monitoring
~~~

**Critical distinctions:** A GCP VPC is a **global** logical network; subnets are **regional**. VPC peering does not automatically provide transitive routing. PSC connects consumers to supported services; private services access (service networking) is a distinct pattern used by some managed services. Private Google Access enables internal-only VM access to supported Google APIs, while Cloud NAT supports outbound translation for workloads without external IPs. Neither implies that an arbitrary public SaaS endpoint is privately reachable.

## 3. VPC modes and IP address design

Use custom-mode VPCs for explicit subnet ownership. Avoid auto-mode in regulated multi-environment platforms: automatic subnets can collide with hybrid ranges. Allocate CIDRs from a central registry; validate overlaps across GCP regions, AWS VPCs, Azure VNets, data centers and Kubernetes Pod/Service secondary ranges. IPv6 support and dual-stack constraints vary by resource; confirm before enabling.

| Layer | Example CIDR | Owner | Constraint |
|---|---|---|---|
| Production subnet | 10.84.0.0/20 | Network platform | no overlap |
| GKE Pods secondary | 10.88.0.0/16 | GKE platform | distinct from subnet/Services |
| GKE Services secondary | 10.89.0.0/20 | GKE platform | distinct from Pods |
| Hybrid on-prem | 10.200.0.0/16 | Enterprise network | route-advertisement review |

All ranges above are illustrative. Reserve room for node growth, alias IP allocation and future regions. For VPC-native GKE, subnet secondary IP ranges and Pod density affect scale. Readdressing production ranges can be disruptive.

## 4. Routing and egress

GCP route selection considers applicable routes, destinations, priorities and next-hop types; never infer an exact path solely from a Terraform route block. Cloud Router dynamically exchanges routes using BGP with supported hybrid connectivity; it is not an ordinary packet-forwarding VM. Cloud NAT translates outbound traffic and does not permit unsolicited inbound connections. Configure sufficient NAT IP/port capacity and monitor port exhaustion during batch ingestion or Kubernetes scale-outs. Private Google Access is configured at subnet level where applicable, and API DNS choices (e.g., restricted/private Google API VIPs) require explicit DNS and route design.

Use route advertisements, firewall policies and Cloud DNS resolution as a coordinated design. GCP routes and firewall rules are separate: reachability requires both a path and permission.

## 5. Firewall rules and hierarchical policy

GCP VPC firewall rules are stateful, with direction, priority, action, protocol/ports and targets (network tags or service accounts). Evaluate implied rules and hierarchical/global/regional network firewall policies in the actual organization. Prefer explicit source ranges, destination service identities and approved port sets; never use \`0.0.0.0/0\` ingress to SSH, RDP, PostgreSQL, Elasticsearch, Redis, MongoDB or Kafka. Logging for relevant allow/deny decisions supports incident reconstruction, but log availability/coverage must be validated.

**Least-privilege baseline:** ingress only from approved ingress/load-balancer health-check and application tiers; database port access only from approved workloads; egress to Google APIs and approved services, with DNS and NTP dependencies understood. Firewall policies should be versioned and tested before promotion.

## 6. Shared VPC and environment boundaries

Shared VPC separates network ownership (host project) from workload ownership (service projects). IAM roles for attaching resources to shared subnets and network administration must be scoped carefully. Use separate dev/staging/prod projects and state backends, explicit subnet attachments and cross-project firewall ownership. VPC peering can connect distinct networks but is not transitive and has overlapping CIDR restrictions. PSC and Cloud VPN/Interconnect solve different problems.

## 7. Private connectivity to data services

For Cloud SQL for PostgreSQL, choose supported private IP / private services access or PSC design based on engine, edition, location and service support. Verify DNS, service networking, IP range allocation, TLS and IAM database authentication where supported. For GKE, account for control-plane endpoint mode, authorized networks/private access, Pod secondary ranges, Cloud NAT and Artifact Registry connectivity. For Memorystore and managed search or message systems, verify the product's actual private connectivity pattern rather than assuming a generic private endpoint exists.

## 8. Observability, reliability and costs

Enable VPC Flow Logs at appropriate sampling/metadata settings and retention, firewall logs, Cloud NAT logs/metrics, VPN/Interconnect/BGP health and Cloud DNS telemetry. Alert on packet drops, denied connections, NAT port allocation errors, DNS SERVFAIL/NXDOMAIN, route changes, BGP down, PSC endpoint errors and unexpected egress spend. Flow Logs are sampled/aggregated and are **not** a complete packet capture. Include cross-region and cross-zone egress, NAT, Cloud VPN, Interconnect and logging charges in FinOps review.

## 9. Terraform architecture

Separate network foundations, shared service projects, firewall policy, hybrid connectivity and workload attachments into modules. Pin provider version and Terraform CLI; use separate GCS state and identities per environment. Review \`terraform plan\` for subnet replacement, route withdrawal, firewall policy removal, PSC endpoint recreation and secondary range changes. Do not rely on \`prevent_destroy\` alone for data-plane safety.

~~~text
network-foundation/
  project-api-enablement/
  shared-vpc-host/
  subnets-and-secondary-ranges/
  firewall-and-hierarchical-policies/
  nat-router-dns/
  private-service-connect/
  service-project-attachments/
  observability-and-runbooks/
~~~

## 10. Executable hands-on labs

Directory: \`infrastructure-as-code/labs/chapter-047/\`.

### Lab A — Offline network architecture contract

~~~bash
cd infrastructure-as-code/labs/chapter-047
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter047.tfplan
terraform apply chapter047.tfplan
terraform output -json
terraform state list
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
~~~

Four \`terraform_data\` resources model VPC/subnet, firewall, private connectivity and operations. Production preconditions reject missing isolation, private data access, restricted ingress, logging and change review. Use distinct state directories for dev/prod.

### Lab B — Policy fixtures and negative tests

~~~bash
python3 network_gate.py fixtures/network-safe.json fixtures/plan-safe.json network-policy.json
python3 network_gate.py fixtures/network-unsafe.json fixtures/plan-destructive.json network-policy.json
python3 -m unittest -v test_network_gate.py
bash run-preflight.sh
~~~

Expected: safe fixture passes, unsafe fixture and destructive plan fail. This is a **declared-control** gate, not a substitute for analyzing real Google provider plans or observed firewall enforcement.

### Lab C — Optional approved GCP sandbox plan

1. Verify GCP project ID/number, billing, API enablement, IAM, Shared VPC ownership and organization policy.
2. Inspect \`examples/google-vpc.tf.example\` as a **separate Terraform root**; its review-only resources can be billable if applied.
3. Confirm subnet/secondary ranges, route overlap, approved firewall targets, DNS, NAT capacity, Private Google Access and connectivity to downstream services.
4. Run \`terraform init\`, \`terraform validate\`, \`terraform plan\` and peer-review all changes; never auto-apply.
5. With change approval, validate isolated sandbox connectivity using non-sensitive workloads, record flow logs and route decisions, and clean up after acceptance.

## 11. Production SRE/DBRE incident scenarios

| Incident | Symptoms | Investigation | Recovery |
|---|---|---|---|
| Subnet CIDR overlap | peering/hybrid connection fails | IP registry, routes, allocated ranges | redesign before apply |
| Firewall regression | TCP timeout / 403 downstream | firewall logs, rule priority/targets | restore narrow known-good policy |
| Cloud SQL inaccessible | DB connection timeout | DNS, PSC/PSA, TLS, network path | recover private service path |
| GKE image pulls fail | ImagePullBackOff | NAT, Private Google Access, Artifact Registry | restore approved egress |
| NAT exhaustion | intermittent outbound failures | NAT port metrics, VM/POD scaling | increase ports/IP capacity |
| DNS outage | SERVFAIL / NXDOMAIN | Cloud DNS zones, forwarders, resolvers | rollback DNS and verify queries |
| Hybrid BGP flap | on-prem connectivity loss | Cloud Router/BGP, tunnel status | fail over and validate routes |
| PSC endpoint unavailable | private service errors | endpoint status, producer acceptance | restore service attachment/path |
| Unexpected public egress | cost/security alert | routes, NAT, firewall, flow logs | quarantine and remediate |
| Terraform subnet replace | destructive plan | state drift, immutable arguments | block, plan migration |

## 12. Troubleshooting command examples

~~~bash
gcloud compute networks list --project=PROJECT_ID
gcloud compute networks subnets list --project=PROJECT_ID
gcloud compute routes list --project=PROJECT_ID
gcloud compute firewall-rules list --project=PROJECT_ID
gcloud compute routers list --project=PROJECT_ID
gcloud compute routers nats list --router=ROUTER --region=REGION --project=PROJECT_ID
gcloud compute vpn-tunnels list --project=PROJECT_ID
gcloud dns managed-zones list --project=PROJECT_ID
terraform providers
terraform state list
~~~

Commands are examples and require permissions. For specific connectivity issues, use Network Intelligence Center Connectivity Tests where available; corroborate predicted paths with logs, DNS and actual application tests.

## 13. Runbooks

**Pre-change:** record project, network owner, source/destination, subnet CIDRs, secondary ranges, firewall policy priority, DNS, routes, NAT, private service endpoints, ticket and rollback. Block overlap or delete/replace changes.

**Database unreachable:** coordinate DBRE; verify client DNS resolution, VPC/PSC/PSA routing, firewall and service health; test TLS and authenticated queries; do not open public DB access as a shortcut.

**NAT port exhaustion:** inspect metrics, connections per VM/pod and autoscaling; expand NAT capacity under approval and validate downstream API latency and error budgets.

**Firewall incident:** preserve change/audit evidence; identify effective policy and target; restore narrowly scoped prior rule and monitor traffic.

**Hybrid outage:** assess BGP sessions, tunnel status, advertisements and route priorities; fail over approved path, measure recovery and application connectivity.

**DNS failure:** verify authoritative zones, private zone attachment, forwarding, TTL and resolver logs; roll back offending record/zone link and confirm DB/GKE access.

**Disaster recovery:** validate network, identity, DNS, KMS and data dependencies together; record measured RPO/RTO. Recreating VPCs does not restore database contents.

## 14. Acceptance (100 points)

| Domain | Points |
|---|---:|
| VPC, subnet, IP and route architecture | 20 |
| Firewall, IAM and environment isolation | 20 |
| Private services, NAT, DNS and hybrid connectivity | 20 |
| Terraform labs and automated negative tests | 15 |
| SRE/DBRE troubleshooting and recovery | 15 |
| Observability, FinOps, approvals and audit | 10 |

Pass >=85/100 with zero critical failures: overlapping production CIDRs, public database ingress, unreviewed destructive subnet changes, missing private connectivity validation or absent DBRE sign-off. Publication and authored tests **do not** constitute live network acceptance.

### Cleanup

~~~bash
terraform destroy -var-file=environments/dev.tfvars
~~~

Only destroy the offline lab or an explicitly disposable approved sandbox.

## 15. Review questions

Why is a GCP VPC global but a subnet regional? How do Cloud NAT and Private Google Access differ? Why can peering not be treated as transitive? Which controls prevent private Cloud SQL exposure? What metrics reveal NAT exhaustion? Why can a successful Terraform apply still leave an application disconnected?

**Next proposed Chapter 048 — GCP IAM, Cloud KMS, Secret Manager and Secure Infrastructure with Terraform.**
