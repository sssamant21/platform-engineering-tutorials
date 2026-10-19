# Chapter 082 — Policy enforcement architecture

1. Source boundary: signed PR, CODEOWNERS, policy-bundle provenance.
2. CI boundary: static scans, OPA/Rego unit tests and provider-specific plan validation.
3. Deployment boundary: protected OIDC, Sentinel where supported, Pulumi CrossGuard, native cloud policy.
4. Kubernetes boundary: admission via Gatekeeper/Kyverno/ValidatingAdmissionPolicy, scoped Argo CD/Flux ownership.
5. DBRE boundary: deny destructive operations without PITR, verified restore and independent approval.
6. Exception boundary: scope, owner, ticket, expiry, compensating control and immutable audit.
7. Runtime: detect drift, SLO regressions and bypassed controls; reconcile and perform incident response.

Fail closed when the policy engine, bundle verification or required evidence is unavailable. Design a separately approved break-glass procedure.
