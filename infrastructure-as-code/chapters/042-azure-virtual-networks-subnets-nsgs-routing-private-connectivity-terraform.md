# Chapter 042 — Azure Virtual Networks, Subnets, NSGs, Routing and Private Connectivity with Terraform

**Part 09 — Azure Infrastructure as Code · Chapter 042/120**  
**Audience:** Platform Engineers, Cloud Network SREs, DBREs, Security Engineers  
**Prerequisites:** Chapter 041, Terraform >=1.7, Python >=3.9  
**Execution boundary:** The default lab is fully offline and uses only Terraform's built-in \`terraform_data\`. AzureRM examples are **review-only**; never apply to a production subscription without approvals and network impact analysis.

## 1. Learning objectives

Design and validate a production Azure network foundation: address-space allocation, VNet/subnet boundaries, NSGs, route tables, NAT, Azure Firewall, hub-and-spoke peering, Private Link/private endpoints, Private DNS, service endpoints, DNS forwarding, AKS integration and private data access. Build executable contract labs and automated network policy tests; prepare incident response for private PostgreSQL, Azure SQL, AKS, Redis and state backend connectivity.

**Success:** no overlapping address spaces, unapproved internet exposure, permissive admin ports, asymmetric routes, unsupported subnet delegation or broken private DNS; all critical changes reviewed and recoverable.

## 2. Reference architecture and data paths

~~~text
                      On-prem / remote networks
                           VPN / ExpressRoute
                                   |
                 Hub VNet (Firewall, DNS resolver, NAT)
                    |                         |
               Peering / UDR             Private DNS
                    |                         |
        Application spoke VNet           Central monitoring
             |             |
      AKS delegated/     App subnet
      node subnet           |
             |          Private endpoint subnet
             +-------------+
                    |
          Private Link to Azure SQL / Storage / Key Vault
                    |
        Database subnet delegated to PostgreSQL Flexible Server
                    |
              Backup + DR controls
~~~

A private endpoint connects to a PaaS resource through a private IP in your VNet; a delegated subnet enables a service to manage resources within that subnet. These are different constructs and often have different subnet requirements. Do not place PostgreSQL Flexible Server VNet-injected resources in an arbitrary private-endpoint subnet.

## 3. Address planning and subnet boundaries

Choose RFC1918 ranges using enterprise IPAM and account for on-premises, peered VNets, DR regions, AKS pod/service CIDRs and future growth. Azure reserves **five IP addresses per subnet**; capacity calculations must subtract these and allow upgrade headroom. Azure VNets support multiple address prefixes, but connected networks must not overlap. Peering does not automatically enable transitive routing.

~~~text
Example only (not globally reserved):
  VNet       10.42.0.0/16
  AKS nodes  10.42.0.0/22
  App        10.42.4.0/24
  Private EP 10.42.5.0/24
  Database   10.42.6.0/24
  Firewall   dedicated hub subnet, not inside app spoke
~~~

Subnet delegation is a control-plane contract; review required delegation names for each Azure service. Plan private endpoints, private DNS and policy rules together.

## 4. NSGs and effective security rules

NSGs attach to subnets or NICs. Rules evaluate priority (lower number first), direction, protocol, source/destination and ports. Stateful return traffic is tracked. Azure default rules permit some VNet and Azure Load Balancer traffic; do not assume an NSG with no custom rules means default-deny. Define explicit least-privilege allow rules and deny exposure for SSH 22, RDP 3389, PostgreSQL 5432, SQL 1433, Redis 6379 and administrative ports.

Prefer Azure Bastion, approved private access and just-in-time controls for management. Review effective NSG rules, application security groups and Azure Firewall policies. A service's own firewall and private endpoint configuration can still deny access even if the NSG permits it.

## 5. Routes, UDRs, peering and NAT

System routes exist by default. User-defined routes (UDRs) can steer egress to Azure Firewall or a network virtual appliance. Verify next-hop type, propagation, peering gateway transit and symmetric return paths. \`0.0.0.0/0\` to a firewall is a forced-tunnel design, not proof of security unless the firewall is available and inspecting traffic. Avoid UDR loops and black holes.

NAT Gateway provides managed outbound SNAT for associated subnets; it is **not** an inbound load balancer or an Azure Firewall substitute. Consider SNAT port exhaustion, scale, zone placement and NAT data-processing costs. Azure Firewall, VPN Gateway, ExpressRoute, private DNS resolver and NAT incur costs.

## 6. Private Link, endpoints and DNS

A private endpoint NIC is created in a subnet; private DNS zones map service FQDNs to private endpoint IPs. Configure zone links to the correct VNets and conditional forwarding for on-premises clients. Use the **service-specific** private DNS zone (for example, Storage Blob commonly uses \`privatelink.blob.core.windows.net\`; other services differ). Azure Database for PostgreSQL Flexible Server with VNet injection has distinct private DNS requirements from Private Link configurations; check the chosen networking mode.

Private endpoints may require approval depending on resource ownership and service settings. Disabling public network access is a separate service-level configuration, not guaranteed by endpoint creation. Validate resolution and TCP/TLS from each client network.

## 7. AzureRM module design and state boundaries

Split network ownership by foundation modules: \`vnet\`, \`subnets\`, \`nsg\`, \`routes\`, \`nat\`, \`private_endpoints\`, \`dns\`, \`diagnostics\`. Export IDs and prefixes; avoid broad cross-module state dependencies. Version and pin providers; use an explicit subscription and tenant from Chapter 041, and separate state for hub, spokes and workloads where operational ownership differs.

For production, maintain a staged plan: IPAM approval → hub and DNS → spoke → NSG/UDR → private endpoints → service configuration → end-to-end probes. Review \`delete\`/\`replace\` actions carefully: network replacement can disconnect databases and workloads even if application resources are unchanged.

## 8. Executable lab layout

~~~text
labs/chapter-042/
  versions.tf, variables.tf, main.tf, outputs.tf
  environments/dev.tfvars, environments/prod.tfvars
  examples/azurerm-network.tf.example
  examples/azure-network-diagnostics.sh.example
  network-policy.json
  fixtures/network-safe.json, network-unsafe.json
  fixtures/plan-safe.json, plan-destructive.json
  network_gate.py, test_network_gate.py, run-preflight.sh
  runbook.md, acceptance.md, .gitignore
~~~

## 9. Lab A — Offline network contracts

~~~bash
cd infrastructure-as-code/labs/chapter-042
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter042.tfplan
terraform apply chapter042.tfplan
terraform output -json
terraform state list
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

The four \`terraform_data\` resources model VNet/subnets, NSG/UDR, Private Link/DNS and observability. No Azure subscription or credentials are needed. Never switch to prod variables against the same local state.

## 10. Lab B — Fail-closed network policy and negative tests

~~~bash
python3 network_gate.py fixtures/network-safe.json fixtures/plan-safe.json network-policy.json
python3 network_gate.py fixtures/network-unsafe.json fixtures/plan-destructive.json network-policy.json
python3 -m unittest -v test_network_gate.py
bash run-preflight.sh
~~~

The safe fixture must pass, the unsafe fixture must fail. Tests cover CIDR overlap, subnet containment, minimum capacity, forbidden management exposure, NSG review, UDR next hops, DNS links, public network access, private endpoints, database delegation, diagnostics, change approvals and destructive plans.

This gate validates **declared network manifests and simplified plan fixtures**, not live Azure effective routes/NSG rules. Production evidence requires Azure Network Watcher, DNS and workload probes.

## 11. Lab C — Optional AzureRM plan-only review

1. Use an approved sandbox subscription, identity and cost budget.
2. Verify Azure tenant/subscription and selected region.
3. Inspect \`examples/azurerm-network.tf.example\` in a separate root, supply approved CIDRs.
4. Run \`terraform init\`, \`terraform validate\`, \`terraform plan\` without automatic apply.
5. Confirm network provider registrations, peering and delegated subnet compatibility, NSG rule precedence, private DNS zone links and public access settings.
6. Record the reviewed plan digest, IPAM approval, rollback, SRE/DBRE owner and change ticket before any live deployment.

## 12. SRE/DBRE production failure scenarios

| Workload | Failure | Signal | Recovery |
|---|---|---|---|
| Azure PostgreSQL | delegated subnet/DNS misconfiguration | connection timeout, NXDOMAIN | verify delegation, private DNS and NSG |
| Azure SQL | Private Link DNS points to public endpoint | unexpected IP, connection deny | repair zone link and client DNS |
| AKS | pod/node subnet IP exhaustion | Pending pods, CNI errors | expand capacity via reviewed network design |
| Redis | route or NSG breaks cache connectivity | timeouts, retries | inspect effective routes and allowed ports |
| Storage backend | firewall denies Terraform blob | init 403, lease errors | restore approved network and RBAC |
| Hub firewall | UDR next hop unavailable | widespread outbound failures | route/failover incident response |
| NAT Gateway | SNAT port pressure | intermittent outbound failures | review connections, scale and architecture |
| On-prem DR | missing conditional forwarder | private FQDN resolution fails | repair DNS forwarding and test |

## 13. Troubleshooting decision matrix

| Symptom | First diagnostic | Avoid |
|---|---|---|
| Private FQDN resolves publicly | DNS zone and VNet links | exposing PaaS public endpoint |
| NSG denies traffic | effective security rules | broad Any/Any allow |
| Traffic takes wrong path | effective routes / next hop | unreviewed 0/0 route |
| AKS networking fails | subnet capacity, CNI, routes | shrinking subnets blindly |
| PostgreSQL cannot connect | DNS, delegation, NSG, TLS | disabling TLS |
| Peering exists but no connectivity | route propagation and NSG | assuming transitive peering |
| Terraform network replacement | immutable attribute/plan | applying destructive changes |
| Private endpoint Pending | connection approval and service policy | enabling public network as shortcut |

## 14. Production runbooks

**Pre-change:** validate IPAM/CIDRs, effective rules, route symmetry, DNS, service private access and recovery → run tests/plan → obtain network, security and DBRE approvals → canary → observe flow logs, DNS, health and SLO.

**DNS outage:** query FQDN from AKS, VM and on-prem; compare expected private IP; inspect private zone, links and resolver forwarding; fix scoped DNS configuration and retest TLS.

**Route black hole:** freeze route deployments, inspect effective routes, firewall/NVA status and peering; restore last reviewed route under incident command; validate both directions.

**DB connectivity:** inspect database subnet delegation, NSG, private DNS, endpoint mode and DB firewall; test TCP/TLS and real query; coordinate with DBRE before any public access change.

**State backend outage:** preserve state and leases, restore Storage private endpoint/DNS/RBAC path; never force-unlock without verifying writer ownership.

## 15. 100-point acceptance

| Domain | Points |
|---|---:|
| IPAM, VNet and subnet architecture | 20 |
| NSGs, routes and egress controls | 20 |
| Private endpoints, DNS and PaaS access | 20 |
| Terraform tests and policy gates | 15 |
| Network observability and incident drills | 15 |
| SRE/DBRE sign-off and change evidence | 10 |

Pass >=85 with no critical failures: overlapping networks, public data exposure, unapproved management ports, destructive plan, missing private DNS validation, or untested DB connectivity.

## 16. Cleanup and review

~~~bash
terraform destroy -var-file=environments/dev.tfvars
terraform state list
~~~

Destroy only disposable offline resources. Questions: Why does VNet peering not imply transit? How does a private endpoint differ from subnet delegation? What are the reserved Azure subnet addresses? Why can NSG and DNS each block a healthy PostgreSQL service? What causes asymmetric routing? Why is a Terraform network plan insufficient to prove connectivity?

**Next: Chapter 043 — Azure Identity, Key Vault, Managed Identities and Secure Infrastructure with Terraform.**
