# Chapter 078 — Hands-on Lab: Jenkins Controller Reliability and Workload Isolation

**Environment:** Disposable Jenkins LTS controller, isolated backup volume, synthetic SCM, test credentials and ephemeral agents. No production fault injection.

## 20 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Inventory controller/state/dependencies | Diagram |
| 02 | Confirm only one writer to Jenkins home | Deployment |
| 03 | Capture core/Java/plugin/JCasC manifest | Manifest |
| 04 | Verify backup integrity and encryption | Report |
| 05 | Configure independent availability probe | Result |
| 06 | Record controller baseline and queue p95 | Metrics |
| 07 | Define release versus PR trust zones | Matrix |
| 08 | Create separate agent pools | Configuration |
| 09 | Test synthetic credential isolation | Access test |
| 10 | Run trusted release-style job | Build |
| 11 | Run untrusted PR-style job | Build |
| 12 | Simulate agent node failure in lab | Events |
| 13 | Verify agent replacement and queue drain | Recovery |
| 14 | Stop test controller under change plan | Timeline |
| 15 | Restore controller and verify single writer | Recovery |
| 16 | Simulate JCasC/plugin regression in lab | Error |
| 17 | Restore known-good image/configuration | Result |
| 18 | Restore backup to separate test namespace | Restore |
| 19 | Measure RTO/RPO and validate representative jobs | Scorecard |
| 20 | Complete incident/DR handover and sign-off | Report |

## 12 failure drills

1. Controller process crash.
2. Startup probe misconfiguration.
3. PVC attach failure.
4. Attempted concurrent writers (configuration review only).
5. Plugin/JCasC regression.
6. Missing synthetic credential provider.
7. Agent node loss.
8. Zone-constrained agent pool.
9. SCM webhook misrouting.
10. Untrusted PR secret access negative test.
11. Backup restore failure.
12. Restore exceeds target RTO.

## Safe verification commands

```sh
kubectl get pods -n jenkins -o wide
kubectl get pvc -n jenkins
kubectl get events -n jenkins --sort-by=.lastTimestamp
kubectl get pods -n jenkins-build -o wide
```

Never start two live controllers against one writable Jenkins home. Restore backups to separate copies.

## Evidence template

```text
UTC timestamp:
Controller core/Java/plugins:
JCasC/image Git SHA:
State volume and single-writer check:
Backup integrity and key handling:
Availability probe:
Trust zones and credential isolation:
Agent pool/zone recovery:
Injected failure and mitigation:
Restore start/finish and measured RTO:
Backup age and measured RPO:
Representative build validation:
Security review:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or explicitly blocked.
- [ ] No shared writable Jenkins home.
- [ ] Backups and encryption keys protected.
- [ ] Trusted/untrusted isolation validated.
- [ ] Controller and agent recovery demonstrated.
- [ ] RTO/RPO measured and reviewed.
- [ ] No production resources disrupted.
- [ ] Handover and reviewer sign-off complete.

**Related:** [Chapter 078 — Jenkins High Availability, Workload Isolation and Controller Reliability Engineering](../078-jenkins-high-availability-workload-isolation-controller-reliability-engineering.md).
