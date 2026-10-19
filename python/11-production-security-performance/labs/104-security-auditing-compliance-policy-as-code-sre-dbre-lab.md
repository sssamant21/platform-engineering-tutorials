# Chapter 104 — Security Auditing, Compliance Automation and Policy-as-Code SRE/DBRE Lab

[Python engine](104/audit_lab.py) · [Automated tests](104/test_audit_lab.py) · [Project guide](104/README.md)

## Mission

Your enterprise platform spans AWS RDS/PostgreSQL, Azure AKS, GCP Cloud SQL and Kubernetes workloads. Security has identified inconsistent audit collection, a broad Azure permission and an unowned Kubernetes workload. Build an evidence-backed, repeatable compliance report and a safe approval-gated advisory change plan.

```text
Synthetic AWS/Azure/GCP/Kubernetes audit evidence
      -> scope + source + timestamp validation
      -> completeness and freshness checks
      -> versioned policy controls
      -> pass/fail/unknown/excepted disposition
      -> SHA-256 report + complete-snapshot drift
      -> approval-gated advisory plan / zero writes
```

## Lab 1 — Execute

```bash
cd python/11-production-security-performance/labs/104
python -m compileall -q audit_lab.py test_audit_lab.py
python -m unittest -v test_audit_lab.py
python audit_lab.py --dry-run
python audit_lab.py --partial
```

## Lab 2 — Audit architecture

Design read-only collectors for AWS CloudTrail/Config/IAM, Azure Activity/Policy/Entra, GCP Audit Logs/Cloud Asset Inventory and Kubernetes API audit/RBAC. Record account/project/subscription/cluster scope, source IDs, timestamps, coverage, retention and collector identity. **No SDK collectors are implemented in this lab.**

## Lab 3 — Control mapping

Map synthetic audit logging, least privilege, encryption-at-rest, ownership and backup verification to appropriate CIS Benchmark configurations, NIST SP 800-53 control families and SOC 2 Trust Services Criteria. Explicitly label the mapping illustrative; an auditor must confirm applicability, control operation and evidence sufficiency.

## Lab 4 — Drift, exceptions and evidence integrity

Reject duplicate or stale evidence, detect new failures between complete snapshots, and return unknown for partial coverage. Add time-limited exceptions with ticket, approver and reason. Demonstrate deterministic SHA-256 report fingerprints and explain why trusted signatures/WORM storage are necessary for tamper resistance.

## Lab 5 — Approval and DBRE incidents

Bind a review plan to provider, scope, resource, control, ticket and expected evidence digest. Test independent approval, expiry, rollback and zero-write behavior. Design a PostgreSQL backup restore-test evidence workflow and a least-privilege database-role review.

## Production incident simulations

| # | Incident | Expected result | Mode |
|---|---|---|---|
| 1 | Four provider evidence records | Normalize | Automated |
| 2 | Unknown provider/control | Reject | Automated |
| 3 | Invalid scope | Reject | Automated |
| 4 | Malformed owner/boolean/timestamp | Reject | Automated |
| 5 | Passing audit evidence | Pass | Automated |
| 6 | Failed least-privilege control | Fail | Automated |
| 7 | Missing owner | Fail | Automated |
| 8 | Stale/future evidence | Unknown | Automated |
| 9 | Partial inventory | Coverage unknown | Automated |
| 10 | Duplicate evidence | Reject | Automated |
| 11 | Canonical report fingerprint | Deterministic | Automated |
| 12 | Modified report | Digest changes | Automated |
| 13 | Approved exception | Excepted | Automated |
| 14 | Expired exception | Fail | Automated |
| 15 | Invalid/duplicate exception | Reject | Automated |
| 16 | New compliance drift | Detect | Automated |
| 17 | Partial-snapshot drift | Unknown | Automated |
| 18 | Multi-page collection | Combine | Automated |
| 19 | Page/item budget exceeded | Fail closed | Automated |
| 20 | Pagination loop/malformed page | Reject | Automated |
| 21 | Advisory plan digest | Deterministic | Automated |
| 22 | Unsupported control/action | Reject | Automated |
| 23 | Changed evidence digest | Plan fingerprint changes | Automated |
| 24 | Missing approval | Hold | Automated |
| 25 | Independent valid approval | Advisory only | Automated |
| 26 | Expired/self approval | Hold | Automated |
| 27 | Wrong digest/missing rollback | Hold | Automated |
| 28 | Approved plan with dry_run=false | Zero writes | Automated |
| 29 | AWS CloudTrail stopped | Investigate account/region coverage | Guided |
| 30 | Azure diagnostic logs absent | Check data-plane logging | Guided |
| 31 | GCP Data Access logs missing | Check configuration and retention | Guided |
| 32 | Kubernetes audit unavailable | Restore policy and sink | Guided |
| 33 | PostgreSQL backup never restored | Run isolated restore test | Guided |
| 34 | MongoDB backup retention drift | Validate restore evidence | Guided |
| 35 | Elasticsearch broad index role | Review permissions and owner | Guided |
| 36 | Evidence manifest checksum mismatch | Quarantine and verify trusted source | Guided |
| 37 | Expired exception after release | Reopen finding | Guided |
| 38 | Collector API throttling | Retry within bounded budget | Guided |

## Troubleshooting and runbooks

**Audit pipeline outage:** establish missing provider/account/region scope, validate collector IAM, API quota, sink health and retention; mark blind spots unknown.

**Compliance drift:** validate source freshness, policy revision, scope, owner and exception; issue a scoped change ticket.

**Evidence integrity:** compare to independently trusted manifest, preserve immutable copies and escalate suspected tampering.

**Exception expiration:** notify risk owner, review compensating controls, re-evaluate finding and remove stale exemption.

**DBRE backup readiness:** restore PostgreSQL/MongoDB backups into isolated environments, validate data and RPO/RTO, retain signed test evidence.

**Least-privilege access:** review AWS/Azure/GCP IAM and Kubernetes RBAC scopes, privilege inheritance, federation and break-glass accounts.

## Final 100-point assessment

| Competency | Points |
|---|---:|
| CIS/NIST/SOC 2 mapping and audit architecture | 20 |
| Multi-cloud/Kubernetes evidence coverage | 20 |
| Policy-as-code, freshness and drift | 20 |
| Evidence integrity and exception governance | 15 |
| Approval gates, least privilege and audit | 15 |
| Automated tests and incident runbooks | 10 |
| **Total** | **100** |

**Pass:** ≥90 points, local tests executed, no-write evidence, documented coverage limitations, signed-evidence production design and independent compliance/security review.

**Validation:** Offline test code published; runtime execution, CI and real provider evidence collection remain pending.
