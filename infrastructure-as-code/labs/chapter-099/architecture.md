# Chapter 099 — Reliability-aware FinOps optimization architecture

**Inputs:** IaC desired state, observed cloud inventory, billing exports, owner tags, p95/p99 capacity, SLO and RPO/RTO.

**Model:** baseline and normalized demand, forecast, commitment utilization, eligible spend, savings estimate, cost basis and uncertainty.

**Decision:** fail-closed cost proposal, independent SRE/DBRE/Finance/Security approvals, no direct deployment authority.

**Execution:** separately authorized staging canary, IaC plan digest, rollback test, production change window.

**Acceptance:** real invoice reconciliation, capacity headroom, error budgets, backup restore, data integrity and audit.

**Boundary:** offline synthetic lab, no live provider integration or automated cloud change.
