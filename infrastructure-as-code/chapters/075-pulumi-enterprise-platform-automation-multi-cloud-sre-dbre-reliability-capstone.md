# Chapter 075 — Pulumi Enterprise Platform Automation, Multi-Cloud SRE/DBRE Reliability Capstone

**Part 15 — Pulumi · Chapter 075/120 · Final enterprise capstone**

## Outcomes

Design and assess a governed multi-cloud Pulumi platform: component architecture, AWS/Azure/GCP provider isolation, encrypted stack state, Automation API orchestration, CI/CD, policy-as-code, observability, backup, disaster recovery and SRE/DBRE incident response. This chapter integrates Chapters 071–074 and completes Part 15. The executable lab is **offline and non-provisioning**; it does not demonstrate real cloud failover, backup restoration or production readiness.

## 1. Reference architecture

~~~text
   Git / signed release / protected PR
                 |
  test + dependency scan + policy gate
                 |
  approved account / subscription matrix
                 |
       CI workload identity (OIDC)
                 |
  Pulumi Automation API orchestrator
                 |
 stack selection / encrypted config / state
                 |
  component resources / dependency graph
         /            |             \
   AWS provider   Azure provider   GCP provider
   EKS / RDS      AKS / PG Flex    GKE / Cloud SQL
         \            |             /
       unified audit / SLO / FinOps
                 |
       canary -> health -> promotion
                 |
   DR plan / PITR / RPO-RTO / handover
~~~

Pulumi resource graphs are scoped by project, stack and provider. AWS accounts/regions, Azure tenants/subscriptions and GCP projects must be independently verified. A Pulumi component is an abstraction, not a security boundary. Provider identities, encrypted state and audit records are separate controls.

## 2. Multi-cloud governance contract

Production delivery requires:
1. Signed source, pinned SDK/CLI/plugins and reviewed component/provider versions.
2. Verified AWS account/region, Azure tenant/subscription and GCP project/region.
3. Short-lived workload identities, least privilege, no plaintext secrets and audited state access.
4. Encrypted/versioned state with restore-tested backup, lock ownership and checkpoint recovery.
5. Fresh preview, signed security/SRE/DBRE approvals, explicit replacement/deletion review.
6. Stateful backup/PITR, replica quorum, recovery objective and restore-drill evidence.
7. Canary deployment, SLO/error-budget checks, bounded concurrency and abort conditions.
8. Cross-cloud consistency design; **never assume automatic provider-to-provider database failover**.
9. FinOps budgets, ownership, resource retention, monitoring and handover.

A declared JSON evidence manifest is useful for a learning exercise but is not a trustworthy production attestation. Real pipelines must obtain verified evidence from identity providers, Pulumi previews, cloud APIs, backup systems, monitoring and signed change approvals.

## 3. Architecture: stateful data across clouds

| Service | AWS | Azure | GCP | DBRE focus |
|---|---|---|---|---|
| Managed PostgreSQL | RDS/Aurora | PostgreSQL Flexible Server | Cloud SQL | PITR, lag, endpoints, failover |
| Kubernetes | EKS | AKS | GKE | PDBs, quotas, identity, storage |
| Cache | ElastiCache | Azure Managed Redis offerings | Memorystore | TTL, client reconnect, data loss |
| Streaming | MSK | Event Hubs / managed Kafka alternatives | Managed Kafka / Pub/Sub alternatives | ISR, ordering, delivery semantics |
| Search | OpenSearch | Managed search alternatives | Managed search alternatives | shard size, IOPS, consistency |

These are **architectural comparisons**, not interchangeable APIs or a deployable cross-cloud DR implementation. Explicitly design CDC, replication, identity, networking, conflict resolution and application cutover before claiming any multi-cloud recovery target.

## 4. Lab A — Offline enterprise deployment contract

~~~bash
cd infrastructure-as-code/labs/chapter-075
python3 enterprise_gate.py fixtures/safe.json policy.json
python3 enterprise_gate.py fixtures/unsafe.json policy.json
python3 -m unittest -v test_enterprise_gate.py test_orchestrator.py
bash run-preflight.sh
~~~

The safe fixture must pass; the unsafe fixture must fail. The gate checks declared account/subscription/project, policy, approval, backup, DR and SLO evidence. It does not parse Pulumi state, verify cloud IAM, evaluate CrossGuard or call providers.

## 5. Lab B — Orchestrator failure injection

The offline state machine enforces:
\`validate -> preview -> approve -> backup -> canary -> health -> promote -> audit\`.

Inject failed preview, unapproved replacement, missing backup, failed canary, SLO regression and missing audit. Every failure must stop promotion. A failed deployment is **not** proof that state was rolled back; preserve checkpoints and assess resources.

## 6. Lab C — Mocked multi-cloud resource graph

Review \`components.py\`, which defines a Pulumi component with three synthetic child resources representing AWS, Azure and GCP targets. Tests use Pulumi runtime mocks; no provider credentials or cloud API calls are used. These mocked resources do not provision real infrastructure or validate provider-specific schemas.

~~~bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python3 -m unittest -v test_components.py
~~~

## 7. Lab D — Disaster recovery and incident tabletop

Simulate a region outage during a three-cloud rollout with an RDS primary replacement preview, Azure PostgreSQL replica lag and a GCP provider identity mismatch. Freeze updates, preserve checkpoints, verify backups and encryption-key access, inspect replication consistency, decide RPO/RTO feasibility, and obtain DBRE/SRE approval before recovery. **Do not execute failover, import state or destroy production resources.**

## 8. Lab E — Enterprise acceptance evidence

Produce: target matrix; signed approvals; pinned dependency manifest; policy-test logs; native Pulumi preview evidence; verified backup/restore logs; SLO dashboard; incident timeline; DR drill; FinOps report; post-change review. Missing any critical evidence blocks acceptance.

## 9. Production incident simulations

| Scenario | Detection | Containment |
|---|---|---|
| Wrong AWS account | caller mismatch | stop |
| Wrong Azure subscription | subscription mismatch | stop |
| Wrong GCP project | project mismatch | stop |
| Stack/backend mismatch | URN or backend mismatch | abort |
| OIDC audience error | claims mismatch | revoke |
| CI token leak | audit finding | rotate |
| Tampered provider plugin | digest mismatch | quarantine |
| SDK/CLI incompatibility | runtime error | pin |
| Component parent rename | unexpected replace | alias review |
| Missing dependency edge | ordering race | halt |
| Secret Output in logs | secret scan | revoke |
| State backend outage | operation failure | freeze |
| Concurrent update lock | lock conflict | identify owner |
| Checkpoint corruption | restore mismatch | isolate |
| Lost encryption key | decrypt failure | preserve ciphertext |
| Unexpected destroy | preview delete | reject |
| RDS/Aurora replacement | data risk | DBRE PITR gate |
| PostgreSQL replica lag | replication alert | stop |
| MongoDB election instability | stepdown | preserve quorum |
| Redis failover | p99 increase | pause |
| MSK ISR shrink | replica alarm | halt |
| OpenSearch disk pressure | IOPS/latency | capacity plan |
| EKS rollout disruption | PDB error | stop |
| AKS node drain failure | eviction error | stop |
| GKE quota exhaustion | scheduling failure | halt |
| Backup integrity failure | checksum mismatch | block |
| RPO/RTO breach | recovery drill | incident command |
| Canary SLO regression | error budget burn | stop promotion |
| Cross-cloud partial rollout | version mismatch | freeze and reconcile |
| FinOps cost spike | budget alert | review |
| Drift after hotfix | refresh delta | reconcile owner |
| Missing audit evidence | compliance gap | reject |

## 10. Production runbooks

**R1 Preflight:** verify project/stack/backend, AWS/Azure/GCP targets, approvals, pins and policy.

**R2 Identity:** check federated token audience/subject, account scopes, RBAC/IAM and token expiry.

**R3 Supply chain:** verify CLI/SDK/provider digests and component provenance.

**R4 Preview:** inspect creates, replacements, deletes, aliases, stateful protections and policy failures.

**R5 Canary:** halt promotion on SLO regression, capture telemetry and decide recovery with owners.

**R6 Stateful recovery:** validate PITR, snapshots, replica lag/quorum, RPO/RTO and restore drills.

**R7 State outage:** preserve checkpoints, confirm lock owner, restore only under change control.

**R8 Cross-cloud incident:** freeze rollouts, evaluate data consistency, network and identity, coordinate DBRE.

**R9 FinOps:** audit retained resources, orphaned storage, tags, budgets and owner.

**R10 Post-change:** verify backups, SLO, state protection, drift, audit and handover.

## 11. Final 100-point assessment

| Domain | Points |
|---|---:|
| Multi-cloud Pulumi architecture, components and providers | 15 |
| Stack identity, state, secrets and recovery | 15 |
| Automation API, CI/CD, workload identity | 15 |
| Governance, previews, policy and approvals | 15 |
| Automated tests and negative scenarios | 15 |
| Stateful DBRE recovery, RPO/RTO and SLO | 15 |
| Runbooks, audit, FinOps and handover | 10 |
| **Total** | **100** |

**Pass:** >=85/100 and zero critical findings with signed SRE/DBRE/security acceptance. Critical failures include wrong target, unauthorized destroy/replacement, leaked secret, missing backup, compromised state, missing approvals, failed SLO or unverified DR.

## 12. Part 15 completion

Chapters 071–075 cover Pulumi fundamentals, resource models/components, stack state/secrets, Automation API/CI delivery and this enterprise multi-cloud capstone. **Publication is complete; actual runtime validation and production acceptance remain pending.**

**Next proposed:** Chapter 076 — Infrastructure as Code CI/CD Foundations, Pipeline Architecture and GitOps Integration (Part 16).
