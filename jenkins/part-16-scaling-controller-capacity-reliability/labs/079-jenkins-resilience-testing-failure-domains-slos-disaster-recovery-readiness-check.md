# Chapter 079 — Hands-on Lab: Jenkins Resilience Testing, SLOs and DR Readiness

**Environment:** Disposable Jenkins LTS, test agents/SCM/artifact registry, synthetic credentials, Prometheus/Grafana and isolated backup volume. Never fault-inject into production.

## 20 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Inventory failure domains | Diagram |
| 02 | Map shared dependencies | Matrix |
| 03 | Define synthetic CI journey | Jenkinsfile |
| 04 | Capture baseline success and latency | Dashboard |
| 05 | Define SLI eligibility and exclusions | Policy |
| 06 | Calculate 30-day availability budget | Worksheet |
| 07 | Define queue and agent p95 SLOs | Spec |
| 08 | Configure synthetic failure alert | Rule |
| 09 | Record controller baseline | Metrics |
| 10 | Inject lab controller process failure | Timeline |
| 11 | Recover controller and verify probe | Evidence |
| 12 | Inject invalid JCasC in staging | Failure |
| 13 | Revert and verify clean build | Recovery |
| 14 | Inject agent label/scheduling fault | Events |
| 15 | Restore compatible agent capacity | Recovery |
| 16 | Simulate SCM/registry outage in lab | Logs |
| 17 | Recover bounded dependency retries | Evidence |
| 18 | Restore backup to isolated state copy | Restore |
| 19 | Measure actual RTO/RPO and integrity | Report |
| 20 | Complete 100-point scorecard and RCA | Sign-off |

## 12 failure drills

1. Controller crash.
2. JVM memory pressure (bounded).
3. Plugin/JCasC regression.
4. Jenkins home disk pressure.
5. Agent node loss.
6. Pod scheduling failure.
7. ImagePullBackOff.
8. Agent remoting failure.
9. NetworkPolicy/DNS failure.
10. SCM webhook/checkout outage.
11. Artifact registry failure.
12. Isolated backup restore failure.

## Executable SLO calculator

```python
from decimal import Decimal

target = Decimal("0.999")
window_days = Decimal("30")
budget_minutes = (Decimal(1) - target) * window_days * Decimal(24) * Decimal(60)
print(f"Availability error budget: {budget_minutes} minutes")
```

Expected: `43.20000 minutes` for 99.9% availability over exactly 30 days. Request-based success budgets use eligible event counts instead.

## Diagnostic commands

```sh
kubectl get pods -n jenkins -o wide
kubectl get events -n jenkins --sort-by=.lastTimestamp
kubectl get pods -n jenkins-build -o wide
kubectl get pvc -n jenkins
```

Do not print secret values. Never attach one writable Jenkins home to two active controllers.

## Evidence worksheet

```text
UTC:
Experiment and owner:
Failure-domain map:
Baseline SLI/SLO:
Error budget:
Fault and blast radius:
Detection/acknowledgment/mitigation/recovery:
Independent synthetic CI:
Rollback and cleanup:
Backup restore integrity:
Measured RTO/RPO:
Security checks:
Score and corrective actions:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or explicitly blocked.
- [ ] SLI/SLO/error budget validated.
- [ ] Synthetic CI and alerting work.
- [ ] Controller and agent recovery demonstrated.
- [ ] Isolated restore completed.
- [ ] RTO/RPO measured and approved.
- [ ] No secrets exposed or production impacted.
- [ ] 100-point assessment reviewed.

**Related:** [Chapter 079 — Jenkins Resilience Testing, Failure Domains, SLOs and Disaster Recovery Readiness](../079-jenkins-resilience-testing-failure-domains-slos-disaster-recovery-readiness.md).
