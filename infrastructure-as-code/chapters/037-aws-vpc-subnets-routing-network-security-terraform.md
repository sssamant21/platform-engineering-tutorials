# Chapter 037 — AWS VPC, Subnets, Routing and Network Security with Terraform

**Part 08 — AWS Infrastructure as Code · Chapter 037/120**  
**Audience:** Platform Engineers, SRE, DBRE, Cloud Security, Network Engineering  
**Prerequisites:** Chapters 001–036 · **Tools:** Terraform >=1.7, Python >=3.9, Bash  
**Safety:** The executable lab is **offline**, using only \`terraform_data\`; it creates no AWS networking resources. AWS provider snippets are review-only examples. Live AWS integration and security acceptance remain pending.

## 1. Objectives

Design a multi-AZ, segmented VPC with predictable CIDR allocations, explicit public/private routing, private databases, least-privilege security groups, layered network ACLs, VPC endpoints, flow logs, and auditable change controls. Translate the architecture into Terraform contracts, test unsafe scenarios, and run SRE/DBRE troubleshooting and recovery procedures.

## 2. Enterprise reference architecture

~~~text
                           Internet
                              |
                       Internet Gateway
                              |
                  Public subnets (AZ-a / AZ-b)
                    ALB + zonal NAT gateways
                      |             |
       private-app-a (AZ-a)   private-app-b (AZ-b)
            |                       |
       private-db-a (AZ-a)    private-db-b (AZ-b)
                \               /
              RDS/Aurora, Redis, OpenSearch
                       |
             Gateway/interface VPC endpoints
                       |
              CloudWatch + VPC Flow Logs
~~~

Use at least two Availability Zones for a production multi-AZ design. AZ names are mapped per AWS account; avoid assuming \`us-east-1a\` is the same physical zone across accounts. Place ALBs/NAT in public subnets and stateful data in private subnets without a default route to an internet gateway or NAT where isolation requires it. A NAT gateway is zonal: each AZ should normally route to its local NAT for resilience, but costs must be reviewed.

## 3. VPC and subnet CIDR planning

A VPC defines an isolated IPv4/IPv6 routing domain. Choose nonoverlapping address space across peered VPCs, Transit Gateway attachments, VPNs and on-premises networks. AWS reserves five IPv4 addresses per subnet. The offline example uses \`10.80.0.0/16\` and six \`/24\` subnets:

| AZ | Public | Private application | Private database |
|---|---|---|---|
| a | 10.80.0.0/24 | 10.80.10.0/24 | 10.80.20.0/24 |
| b | 10.80.1.0/24 | 10.80.11.0/24 | 10.80.21.0/24 |

For IPv6, explicitly consider egress-only internet gateways, security group rules, DNS and dual-stack application compatibility. Never assume IPv4 NAT protects IPv6 routes.

## 4. Routing and gateways

- **Public route table:** \`0.0.0.0/0 → igw\`; an internet-facing resource also needs appropriate addressing and security controls.
- **Private application route table:** \`0.0.0.0/0 → same-AZ NAT gateway\` if outbound internet is approved; otherwise use required VPC endpoints.
- **Private database route table:** local VPC routes only, plus explicitly approved service endpoints or private transit routes. No internet default route.
- **Gateway endpoints:** S3/DynamoDB route table integration; endpoint policies and IAM still matter.
- **Interface endpoints:** private IPs in subnets, private DNS and endpoint security groups; review hourly and data-processing costs.
- **Transit Gateway / peering:** route propagation, asymmetric paths, overlapping CIDRs and security boundaries need independent review.

A route table only chooses a path; it does not replace security groups, NACLs, IAM or TLS.

## 5. Security groups and NACLs

Security groups are **stateful** and attach to ENIs. Prefer explicit source security-group references, tightly scoped ports, and dedicated groups for ALB, application and database tiers. Security group rules alone do not authenticate the application.

NACLs are **stateless**, subnet-scoped and require both directions, including ephemeral return ports. Use them as coarse guardrails, not a substitute for security groups. Broad deny/allow mistakes can break DNS, health checks, replication and cross-AZ recovery. Avoid open database ports such as 5432, 3306, 27017, 6379 and 9200 from \`0.0.0.0/0\` or \`::/0\`.

## 6. Terraform AWS network design

The production-oriented snippets in \`examples/aws-network.tf.example\` illustrate \`aws_vpc\`, \`aws_subnet\`, \`aws_internet_gateway\`, \`aws_route_table\`, \`aws_route_table_association\`, \`aws_security_group\`, and \`aws_vpc_endpoint\`. Review current AWS provider schemas before using them.

Use stable \`for_each\` keys such as \`public_a\` and \`private_db_b\` rather than \`count\` indexes for long-lived subnets. Separate network foundations from DB/application roots and pass minimal outputs (subnet IDs, security group IDs). Protect route and subnet address changes with plan review and stateful-service impact analysis.

## 7. Hands-on lab directory

~~~text
labs/chapter-037/
  versions.tf, variables.tf, main.tf, outputs.tf
  environments/dev.tfvars, environments/prod.tfvars
  examples/aws-network.tf.example, examples/network-diagnostics.sh.example
  network-policy.json
  fixtures/network-safe.json, network-unsafe.json
  fixtures/plan-safe.json, plan-destructive.json
  network_gate.py, test_network_gate.py, run-preflight.sh, .gitignore
~~~

The offline Terraform root models VPC CIDR, AZ/subnet allocation, route intents, SG ingress, logging and endpoint controls. It does **not** provision VPCs or enforce AWS-side policy.

## 8. Lab A — Offline topology contracts

~~~bash
cd infrastructure-as-code/labs/chapter-037
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter037.tfplan
terraform apply chapter037.tfplan
terraform output -json
terraform state list
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

Expected: \`terraform_data.vpc_contract\`, \`terraform_data.subnet_contract\`, \`terraform_data.routing_contract\`, \`terraform_data.security_contract\`. Second unchanged plan should return exit 0. Never apply prod inputs against dev local state.

## 9. Lab B — Fail-closed network policy and tests

~~~bash
python3 network_gate.py fixtures/network-safe.json fixtures/plan-safe.json network-policy.json
python3 network_gate.py fixtures/network-unsafe.json fixtures/plan-destructive.json network-policy.json
python3 -m unittest -v test_network_gate.py
bash run-preflight.sh
~~~

Expected: safe fixture passes, unsafe fixture denied. Tests exercise invalid CIDRs, overlap, AZ coverage, public database routing, open database ingress, wrong NAT mapping, disabled flow logs, missing endpoints, tags, approval, state isolation and delete/replace plans.

**Important:** Python validates a declared topology manifest, not actual AWS routing tables. A separate live plan, AWS Config/Reachability Analyzer and runtime connectivity checks are required for production acceptance.

## 10. Lab C — Optional AWS network plan review

1. Obtain an approved sandbox account, region and budget.
2. Verify \`aws sts get-caller-identity\`, IAM role and account allowlist.
3. Review the example file; adapt subnet AZ names, tags, cost controls, NAT and endpoints.
4. Use a separate root and remote backend; run \`terraform init\`, \`terraform validate\`, \`terraform plan\`.
5. Inspect all routes, subnet associations, security group ingress/egress and endpoint policies.
6. Confirm no destructive stateful-service changes; do not apply automatically.

## 11. Production SRE/DBRE scenarios

| Scenario | Failure mode | Acceptance evidence |
|---|---|---|
| RDS/Aurora PostgreSQL | DB subnet route/SG blocks replicas or clients | connection tests, replication lag, Multi-AZ failover |
| EKS | CNI IP exhaustion, node route/NAT issue | free IPs, pod scheduling, API and node health |
| OpenSearch | cross-AZ traffic or SG blocks transport | shard allocation, node health, query p99 |
| Redis | client/replica port blocked | failover and reconnect |
| MSK/Kafka | broker DNS/port path blocked | ISR, consumer lag, produce/consume |
| S3 endpoints | route/policy denies backup | backup and restore checks |
| Hybrid routing | asymmetric TGW/VPN path | bidirectional traceroute, flow logs, route tables |

## 12. Troubleshooting and incident simulations

| Symptom | Likely cause | Safe action |
|---|---|---|
| Private instances cannot reach package repositories | NAT route, NACL or DNS | inspect route association, zonal NAT and resolver |
| Database suddenly reachable from internet | SG/route/public address regression | contain access, audit and rotate exposed credentials |
| One AZ fails while another works | NAT/AZ route mismatch | inspect AZ-specific route tables |
| Cross-VPC traffic fails | overlap or TGW route propagation | verify CIDRs, attachment tables and return path |
| S3 access denied through endpoint | endpoint policy or IAM | compare identity, bucket and endpoint policies |
| TLS handshake fails | SG/NACL/MTU/DNS | collect flow logs and packet/connection evidence |
| High NAT bill | cross-AZ egress or endpoint absence | review flow and billing metrics |
| Terraform wants to replace subnet | immutable CIDR/AZ argument | freeze, assess DB/EKS impact and migration |

**Game day 1:** remove a required app→DB SG edge in a disposable environment and prove detection/recovery.  
**Game day 2:** point a private AZ route at another AZ's NAT and detect resilience/cost risk.  
**Game day 3:** model a public DB ingress rule and prove the policy gate rejects it.  
**Game day 4:** model an unapproved subnet replacement and verify CI blocks it.

## 13. Production runbooks

**Network deployment:** verify account/region and backend → CIDR overlap review → route and SG diff → network/security approval → plan-policy gate → deploy in maintenance window → connectivity, DNS, Flow Logs and DBRE acceptance.

**Network outage:** declare incident → identify blast radius by AZ/tier → preserve route/SG changes and flow logs → verify DNS, NAT, NACL and return path → rollback only reviewed change → validate application and DB health.

**Unexpected exposure:** isolate offending SG/route → inspect CloudTrail and flow logs → rotate credentials as appropriate → notify security → preserve audit evidence → implement least-privilege fix.

**Subnet migration:** inventory ENIs, EKS nodes, RDS subnet groups and IP demand → create new subnets → stage workloads → drain/replicate safely → cut over and observe → decommission only after data/service acceptance.

**DR:** verify cross-region address allocation, routing, endpoints, DNS, replication and RPO/RTO. Terraform state recovery does not restore databases.

## 14. 100-point acceptance rubric

| Domain | Points |
|---|---:|
| CIDR/subnet/AZ architecture | 20 |
| Routes, NAT and endpoints | 20 |
| SG/NACL least privilege | 20 |
| Automated negative tests and plan gates | 20 |
| Observability, troubleshooting and DBRE runbooks | 15 |
| Change/audit evidence | 5 |

Pass >=85, with zero critical failures: internet-exposed DB port, overlapping production CIDR, missing required AZ isolation, unauthorized delete/replace, unverified route change or false DR claim.

## 15. Cleanup and review

~~~bash
terraform destroy -var-file=environments/dev.tfvars
terraform state list
~~~

Destroy only the disposable local lab. Review: Why are NACLs stateless? What does a route table not protect? Why use same-AZ NAT? What makes a subnet public? Why avoid \`count\` for stable subnets? How do endpoint policies interact with IAM? What does Flow Logs prove? Why can a network plan be correct but database recovery fail?

**Next: Chapter 038 — AWS IAM, KMS, Secrets and Secure Infrastructure with Terraform.**
