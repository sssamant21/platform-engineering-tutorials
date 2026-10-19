# Chapter 074 — Pulumi Automation API and CI/CD Runbooks

## R1 Pipeline preflight
Validate signed source, runner, project, stack, backend, target and provider pins.

## R2 Identity
Verify OIDC audience/subject, scoped role, token expiry and protected environment.

## R3 Preview review
Inspect creates, deletes, replacements, drift, policy findings and approval.

## R4 Lock conflict
Identify active operation; preserve logs; never blindly clear locks.

## R5 Partial update
Freeze later stages; capture checkpoint and events; obtain SRE/DBRE approval.

## R6 Stateful recovery
Verify PITR, backups, replicas, RPO/RTO and restore drill.

## R7 Canary SLO failure
Stop promotion, inspect telemetry, choose owner-approved rollback/forward-fix.

## R8 Supply chain
Quarantine artifacts, revoke credentials, rebuild from pinned inputs.

## R9 FinOps
Review unexpected additions, retained resources, tags and budgets.

## R10 Post-deployment
Verify SLO, backup, encryption, audit trail, drift and handover.
