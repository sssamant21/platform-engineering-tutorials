# Chapter 028 — Alertmanager Notification Templates and Delivery Reliability Lab

**Part 06 — Alertmanager and Alert Engineering.** Python 3.10+ offline governance, optional staging-only receiver delivery.

## 1. Files

Copy the five complete blocks from [Chapter 028](../028-alertmanager-notification-templates-receiver-integrations-security-delivery-reliability.md) into:

```text
chapter028/
  templates/notifications.tmpl
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/notification_gate.py
  tests/test_notification_gate.py
```

## 2. Execute

```bash
cd chapter028
python3 scripts/notification_gate.py fixtures/healthy.json
if python3 scripts/notification_gate.py fixtures/degraded.json; then exit 1; fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL and 29 tests PASS.

## 3. Twelve failure drills

1. Receiver has an external endpoint.
2. Secret embedded instead of external reference.
3. Duplicate receiver name.
4. Missing fallback route.
5. Backup and primary route identical.
6. Receiver timeout zero.
7. Resolved notifications disabled.
8. Missing receiver owner.
9. Unsafe grouping.
10. Runbook field omitted.
11. Sensitive payload permitted.
12. Missing delivery SLO review.

Modify copies of the synthetic fixtures and capture gate output.

## 4. Optional staging integration

Use Chapter 026's local webhook and a synthetic alert. Validate native config with `amtool`, verify webhook receipt and resolution, then simulate receiver errors with a dedicated test-only handler. Templates must be wired only to receiver types supporting custom message fields. No production paging endpoints.

## 5. DBRE tabletop

During PostgreSQL failover, a webhook returns 429, a runbook annotation is missing and a secret rotation interrupts notification delivery. Recover the receiver, test backup routing and document firing-to-acknowledgement timing.

## 6. Evidence

```text
UTC / operator / environment:
Receiver/template version:
Secret source / fallback:
Healthy/degraded gate / 29 tests:
12 negative drills:
Optional receiver test / resolved event:
RCA / rollback / reviewer / score:
```

**Acceptance:** 29 tests pass, degraded fixture rejected and delivery readiness is separately verified in staging.
