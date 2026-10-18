# Chapter 047 — GCP Network SRE/DBRE Runbooks

## Change preflight
Confirm project, network owner, subnet and GKE secondary CIDRs, hybrid overlaps, firewall hierarchy, DNS, NAT, private service connectivity, quotas, flow logs and DBRE/security approvals. Block destructive changes.

## Cloud SQL private connectivity outage
Validate client DNS, Private Service Connect or private services access mode, VPC routes, firewall, TLS, IAM and database health. Avoid public database exposure.

## Cloud NAT exhaustion
Inspect NAT port metrics and connection fan-out; review GKE scale, add NAT capacity with approval and validate API error rate.

## Firewall policy regression
Inspect effective rule priorities and hierarchical policies, targets, source/destination and logs. Restore narrow prior rule; preserve audit trail.

## Hybrid BGP outage
Inspect Cloud Router BGP sessions, Cloud VPN/Interconnect status and advertisements. Fail over approved route and verify downstream queries.

## DNS outage
Review private zones, forwarding, TTL and resolver health. Roll back bad zone/record and test DB, GKE and API connectivity.

## DR and rollback
Recover IAM, VPC, DNS, KMS and data in dependency order. Record measured RPO/RTO and database integrity; Terraform state alone does not recover data.
