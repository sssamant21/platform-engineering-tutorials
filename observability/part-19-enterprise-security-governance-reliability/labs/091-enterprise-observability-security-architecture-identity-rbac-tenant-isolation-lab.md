# Chapter 091 — Enterprise Observability Security, RBAC and Tenant Isolation Lab

## Offline validation

Copy `healthy.json`, `security_gate.py` and `test_security_gate.py` from [Chapter 091](../091-enterprise-observability-security-architecture-identity-rbac-tenant-isolation.md).

```bash
python3 security_gate.py healthy.json
python3 -m unittest -v test_security_gate.py
```

Expected PASS and 32 authored tests; record actual output.

## Isolated staging security game day

1. Inventory identities, service accounts, tokens, certificates and trust boundaries.
2. Verify Grafana SSO group mappings, folder roles and datasource permissions.
3. Review Kubernetes RBAC and network policies; use read-only inspection first.
4. Validate Prometheus and Alertmanager API authentication.
5. Configure two synthetic Loki/Tempo tenants with separate identities.
6. Attempt authorized tenant A query and unauthorized tenant B query; confirm denial.
7. Test collector token revocation and controlled certificate rotation.
8. Inject synthetic sensitive log/span attributes and verify redaction.
9. Capture security audit events, restore original policy and verify service SLOs.
10. Complete the 100-point assessment with security and on-call approval.

## Negative drills

Reject spoofed tenant headers, overbroad service accounts, public object storage, plaintext OTLP, unapproved exporters and absent audit records.

## Evidence worksheet

```text
UTC / owner / change ID:
Identity and group mappings:
RBAC / datasource access:
Tenant A/B isolation tests:
Collector TLS and secret rotation:
Redaction checks:
Storage IAM / network policy:
Incident / rollback / SLO:
Offline tests and acceptance score:
```

Synthetic PASS does not establish actual tenant isolation or security compliance.
