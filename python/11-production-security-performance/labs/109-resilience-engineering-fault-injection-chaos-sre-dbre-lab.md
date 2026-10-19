# Chapter 109 — Resilience Engineering and Chaos Testing: SRE/DBRE Lab

[Python simulator](109/resilience_lab.py) · [Automated tests](109/test_resilience_lab.py) · [Project guide](109/README.md)

## Scope and safety

All exercises run locally with synthetic data. No network connections, cloud mutations, live disruptions or database writes are performed. Production chaos requires separately authorized change management; this lab never authorizes or executes it.

## Lab 1 — Run

```bash
cd python/11-production-security-performance/labs/109
python -m compileall -q resilience_lab.py test_resilience_lab.py
python -m unittest -v test_resilience_lab.py
python resilience_lab.py --dry-run
```

## Lab 2 — Retry and backoff

Explore capped exponential backoff, deterministic jitter, max attempts and simulated deadlines. Verify non-idempotent operations are blocked from automatic retries. Explain safe idempotency keys and why remote transaction outcomes must be checked after timeouts.

## Lab 3 — Circuit breakers and bulkheads

Exercise closed, open and half-open breaker transitions. Simulate bounded worker capacity and queue admission. Identify missing production requirements: thread-safe state, bounded half-open probes and distributed coordination.

## Lab 4 — SLO and controlled experiment design

Calculate remaining error budget and design a hypothetical staging-only experiment with approval, baseline health, rollback readiness and limited scope. The simulated gate returns advisory status; it performs no fault injection.

## Lab 5 — SRE/DBRE investigation

Design diagnostic playbooks for PostgreSQL connection pool exhaustion, Elasticsearch 429 responses and storage latency, MongoDB primary transitions, Kafka consumer lag, Kubernetes readiness failures and Redis cache stampede.

## Automated regression scenarios

The published unit tests cover: backoff base/growth/cap, reproducible jitter, invalid values, retry success/exhaustion, non-idempotent blocking, deadline handling, breaker opening/rejection/half-open/recovery, bulkhead overload, timeout budgets, staging-only simulated approval, missing rollback, unhealthy baseline, exhausted error budget, excessive scope, SLI evaluation, and zero network or mutation behavior.

## Guided production scenarios

1. PostgreSQL connection pool exhaustion: measure aggregate pool limits and wait time.
2. PostgreSQL uncertain commit: verify remote result before replay.
3. Elasticsearch rejection storm: reduce fanout and use bounded backoff.
4. Elasticsearch storage pressure: inspect IOPS and queue depth.
5. MongoDB primary transition: review driver retry semantics.
6. Kafka rebalance: protect offset and ordering correctness.
7. Kubernetes pod readiness regression: stop rollout and verify recovery.
8. Redis cache outage: protect backing database capacity.
9. Breaker flapping: examine dependency health and probe settings.
10. Staging experiment abort: restore baseline and validate SLOs.

## Runbooks

**Retry storm:** inspect request amplification, retries, error classes and downstream saturation. Cap attempts, throttle ingress and verify recovery.

**Breaker open:** confirm failure classification, reset interval and dependency readiness before controlled recovery.

**Uncertain database write:** verify transaction and idempotency records before any replay.

**Bulkhead saturation:** measure active/queued/rejected requests and protect priority workloads.

**Experiment abort:** restore baseline, validate data integrity and document observations.

## Final 100-point assessment

| Competency | Points |
|---|---:|
| Retry and deadline policy | 20 |
| Breaker and bulkhead behavior | 20 |
| Experiment safety and approval design | 20 |
| SLO/error-budget analysis | 15 |
| Incident troubleshooting and runbooks | 15 |
| Automated tests and reproducibility | 10 |
| **Total** | **100** |

Pass at 90 or above with locally executed tests, no-mutation evidence, and a reviewed rollback plan.

**Validation:** Code and tests are published; execution of the exact committed revision, CI and live integrations remain pending.
