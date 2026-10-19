# Chapter 094 — Enterprise IaC SLO architecture

**Source:** protected Git, reviewed plan, change ticket, policy and immutable artifact.

**Signals:** IaC deployment metrics, Prometheus request SLIs, OpenTelemetry logs/traces, cloud audit, GitOps, DBRE health.

**Data quality:** trusted provenance, freshness, eligibility denominator, cardinality and UNKNOWN on missing data.

**Objectives:** service tier SLO, error budget, 5m/1h and 30m/6h burn-rate windows.

**Response:** Alertmanager routes, incident commander, SRE/DBRE/security, staged promotion, HOLD/QUARANTINE.

**Controls:** no autonomous destructive remediation, independent approval, state backup, rollback and DR.

**Acceptance:** live page delivery, customer SLO, measured RPO/RTO and audit evidence.

**Boundary:** offline Python fixtures only.
