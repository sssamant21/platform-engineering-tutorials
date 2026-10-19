# Chapter 076 — IaC CI/CD Operations Runbooks

1. **R1 PR preflight:** freeze promotion; inspect provenance, dependency pins, lint/unit/security.
2. **R2 OIDC:** verify audience, subject, role scope and expiration; revoke compromised trust.
3. **R3 Backend lock:** identify active operation, preserve checkpoint; never force-unlock blindly.
4. **R4 Plan review:** regenerate after drift; inspect destroy/replacement, target and approvals.
5. **R5 Stateful DBRE:** verify PITR, backup checksum, replica quorum, RPO/RTO, restore drill.
6. **R6 GitOps drift:** compare Git, cluster and controller health; reconcile ownership.
7. **R7 Partial apply:** halt, preserve logs/state, assess cloud changes and recover safely.
8. **R8 Canary SLO:** stop promotion on p99/error budget regression; coordinate rollback.
9. **R9 Supply chain:** quarantine runner/artifact, rotate tokens, rebuild signed pins.
10. **R10 Handover:** archive plan, approval, execution, metrics, backup and incident evidence.
