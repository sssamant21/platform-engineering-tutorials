# Chapter 093 — Enterprise IaC incident correlation architecture

**Source:** protected Git, change ticket, reviewed plan and immutable artifact.

**Event streams:** CI/CD, Terraform/OpenTofu, AWS/Azure/GCP audit, Kubernetes/GitOps, OTel logs/traces/metrics, DBRE telemetry.

**Normalization:** exact target, UTC event and ingestion timestamps, source provenance, change ID, service topology.

**Hypotheses:** bounded temporal correlation plus dependency overlap, independent evidence and contradictory observations; never assert causality from timing alone.

**Response:** incident commander, SRE/DBRE/security, bounded rollback, DR restore and SLO verification.

**Audit:** immutable evidence, blameless postmortem, corrective action owner and due date.

**Boundary:** Python labs use synthetic fixtures only.
