# Chapter 088 — Compliance assurance architecture

**Control catalog:** ID, objective, owner, risk, framework mapping, native policy, evidence, frequency, retention.

**Preventive gates:** PR approvals, secret/IaC scans, signed provenance, OPA/Sentinel, cloud IAM/org policy and K8s admission.

**Detective controls:** CloudTrail, Azure Activity Logs, GCP Audit Logs, Kubernetes audit, GitOps drift, CSPM and DBRE SLO.

**Evidence:** independently trusted source, immutable timestamp, source SHA, target, policy bundle, artifact hash, retention and chain of custody.

**Remediation:** exception owner, independent approver, compensating control, expiry, DBRE recovery and retest.

**Limitation:** synthetic offline lab does not validate native enforcement or certify compliance.
