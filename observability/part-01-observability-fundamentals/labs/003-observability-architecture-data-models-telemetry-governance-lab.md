# Chapter 003 — Hands-on Lab: Observability Architecture and Governance

**Safety:** Offline synthetic JSON and Python validation only. No cloud credentials or production data.

## Setup

Create the following files from the complete source blocks in [Chapter 003](../003-observability-architecture-data-models-telemetry-governance.md):

```text
chapter003/
  fixtures/approved.json
  fixtures/rejected.json
  scripts/validate_contract.py
  tests/test_contract.py
```

## Execute

```bash
cd chapter003
python3 scripts/validate_contract.py fixtures/approved.json
if python3 scripts/validate_contract.py fixtures/rejected.json; then
  echo "FAIL: unsafe contract accepted"; exit 1
else
  echo "PASS: unsafe contract rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: approved fixture exits zero; rejected fixture exits nonzero; eight unit tests pass.

## 12 targeted failure drills

1. Remove service owner.
2. Route telemetry to unapproved region.
3. Add patient_id as metric label.
4. Increase log retention beyond policy.
5. Disable tenant isolation.
6. Disable RBAC review.
7. Disable TLS/encryption-in-transit.
8. Disable encryption at rest.
9. Exceed metric series budget.
10. Set invalid sample interval.
11. Add authorization to sensitive fields.
12. Remove cost center.

For each drill, record validator output, production mitigation and responsible reviewer.

## Architecture tabletop

A new service emits 100,000 patient-specific label values, exports logs to an unapproved region and retains debug traces indefinitely. Identify privacy, compliance, cost, availability and response impacts. Propose source-side redaction, bounded labels, regional routing, approved retention and change controls.

## Evidence

```text
UTC / operator:
Architecture and data classification:
Approved fixture result:
Rejected fixture result:
Eight unit tests:
Cardinality estimate:
Regional and retention checks:
12 failure drills:
RCA / COA / reviewer:
```

- [ ] Approved fixture accepted.
- [ ] Rejected fixture denied.
- [ ] Eight tests pass.
- [ ] Data classification and ownership documented.
- [ ] Regional, retention, encryption and RBAC controls reviewed.
- [ ] Cardinality and FinOps impact estimated.
- [ ] No claim of real compliance certification from synthetic validation.
