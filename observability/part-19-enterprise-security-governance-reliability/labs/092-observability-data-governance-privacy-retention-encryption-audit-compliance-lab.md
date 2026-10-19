# Chapter 092 — Observability Governance, Privacy, Retention and Audit Lab

## Offline acceptance

Copy `healthy.json`, `governance_gate.py` and `test_governance_gate.py` from [Chapter 092](../092-observability-data-governance-privacy-retention-encryption-audit-compliance.md).

```bash
python3 governance_gate.py healthy.json
python3 -m unittest -v test_governance_gate.py
```

Expected PASS and 30 authored tests; record actual results.

## Isolated staging game day

1. Classify synthetic metrics, logs, spans, exemplars and alert payloads.
2. Map owners, processors, tenants, storage and regional data flows.
3. Inject synthetic sensitive values and test pre-ingest redaction.
4. Verify Grafana, Loki and Tempo tenant access restrictions.
5. Review Prometheus/Loki/Tempo retention and object-store lifecycle settings.
6. Verify TLS, storage encryption, KMS IAM and audit logging.
7. Rotate a staging key and test a staging backup restore.
8. Test denied access and denied export audit evidence.
9. Reconcile policy changes through GitOps with approved rollback.
10. Complete the 100-point assessment and obtain privacy/security approval.

## Negative drills

Reject sensitive labels, incomplete audit trails, unauthorized data export, unapproved retention deletion, non-restorable encrypted backups and expired policy exceptions.

## Evidence

Record UTC, dataset classification, owner, data flow, redaction result, tenant tests, retention proof, KMS restore evidence, audit records, actual offline test output and sign-off. Synthetic PASS is not a compliance certification.
