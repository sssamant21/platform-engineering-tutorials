# Chapter 042 — Azure networking SRE/DBRE runbooks

## Network change
Verify tenant/subscription, IPAM CIDRs, subnet capacity, effective NSG rules, UDR next hops, DNS zones/links, service private access and backup connectivity. Run policy tests and plan; inspect replacements. Obtain network, security and DBRE approvals. Canary, monitor and validate private FQDN and application SLO.

## Private DNS outage
From AKS, VM and on-prem clients, resolve private service FQDN. Check private DNS zone, VNet link, conditional forwarding and resolver health. Repair scoped DNS and verify TCP/TLS plus real database query.

## NSG deny
Inspect effective NSG rules and priorities at subnet and NIC, service firewall and Azure Firewall. Fix narrow rule only after approval; do not allow Any/Any or open DB ports publicly.

## Route black hole
Stop UDR deployment, inspect effective routes, next-hop firewall/NVA, peering and gateway transit; restore last reviewed route under incident command and test symmetric traffic.

## PostgreSQL outage
Validate delegated subnet, private DNS mode, route, NSG, database state and TLS. Confirm query integrity and DBRE SLO before closure.

## Azure Storage state outage
Preserve state blob versions and leases. Diagnose Storage private endpoint, DNS, RBAC and firewall. Never force-unlock without confirming the active writer.
