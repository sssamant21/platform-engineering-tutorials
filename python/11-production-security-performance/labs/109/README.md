# Chapter 109 — Resilience Engineering, Fault Injection and Chaos Testing Lab

[Offline simulator](resilience_lab.py) · [Automated tests](test_resilience_lab.py) · [Complete SRE/DBRE lab](../109-resilience-engineering-fault-injection-chaos-sre-dbre-lab.md)

## Run locally

Python 3.11+ standard library only. No external dependencies, credentials, network access, sleeps, actual fault injection or production writes.

```bash
cd python/11-production-security-performance/labs/109
python -m compileall -q resilience_lab.py test_resilience_lab.py
python -m unittest -v test_resilience_lab.py
python resilience_lab.py --dry-run
```

PowerShell: `py -3 -m unittest -v test_resilience_lab.py`.

## Implemented

- Deterministic capped exponential backoff with bounded jitter.
- Idempotency-aware retry plans with max attempts and simulated deadline.
- Sequential circuit breaker closed/open/half-open transitions.
- Bulkhead active/queued/rejected admission model.
- Timeout budget calculations across attempts.
- SLI and remaining error-budget evaluation.
- Chaos policy gate with environment, approval, rollback, health, budget and blast radius.
- Synthetic PostgreSQL incident simulation.
- **Zero real fault injection, network calls, resource mutations or production changes.**

## Exercises

1. Validate backoff growth, cap, jitter and invalid inputs.
2. Compare successful, exhausted, deadline-limited and non-idempotent retry plans.
3. Transition circuit breaker through closed/open/half-open.
4. Model bounded queue and bulkhead overload.
5. Verify nested timeouts fit the total deadline.
6. Block production chaos and missing approval/rollback.
7. Deny experiments with unhealthy baseline or exhausted error budget.
8. Calculate SLO availability and remaining bad-event budget.
9. Simulate PostgreSQL pool exhaustion.
10. Design Elasticsearch 429/retry-storm mitigation.
11. Write MongoDB failover and Kafka consumer-rebalance runbooks.
12. Define a staging-only chaos hypothesis, abort criteria and rollback evidence.

## Production extension — NOT implemented

Integrate approved retry/circuit-breaker libraries, bounded async client pools, real OpenTelemetry metrics, Toxiproxy or Chaos Mesh in isolated staging, authorization workflow, rollback automation and audit trail. Test thread safety, half-open probe limits, transaction idempotency and actual deadline propagation. Do not enable production fault injection from this lab.

## CI template (not enabled)

```yaml
name: chapter-109-resilience-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/11-production-security-performance/labs/109
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q resilience_lab.py test_resilience_lab.py
      - run: python -m unittest -v test_resilience_lab.py
```

Pin reviewed action commit SHAs before enabling. **Validation:** Test source published; execution of exact committed revision, CI, real fault injection and production acceptance remain pending.
