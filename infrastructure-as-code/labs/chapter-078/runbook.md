# Chapter 078 — Production SRE/DBRE runbooks

1. **Target preflight:** verify Pulumi stack/backend, CloudFormation account/region, Azure tenant/subscription/scope.
2. **Identity:** validate OIDC claims, role scopes, protected runners, signed commits and dependency pins.
3. **Pulumi preview:** review resource changes, aliases, locks, secret provider and policy findings.
4. **CloudFormation:** inspect change set, replacement flags, capabilities, StackSets scope and rollback state.
5. **Bicep:** validate scope, what-if changes, deployment stack deletion risk, Azure Policy and RBAC.
6. **Approval:** bind independent SRE/security/DBRE approval to digest, target, commit and ticket.
7. **DBRE recovery:** verify PITR, backup integrity, quorum, RPO/RTO and successful restore rehearsal.
8. **Partial update:** freeze promotion; preserve checkpoints and investigate actual cloud resources.
9. **Canary:** stop on SLO/error-budget breach; coordinate rollback/forward fix with service owners.
10. **Audit:** retain immutable change evidence, service health, state backup and handover.
