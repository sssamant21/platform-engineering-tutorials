# Chapter 023 — Grafana Dashboard GitOps and Reusable Libraries Lab

**Part 05 — Grafana Dashboards and Visualization.** Offline Python 3.10+ governance checks, optional staging Grafana.

## 1. Project files

Copy the six complete JSON/Python blocks from [Chapter 023](../023-grafana-advanced-dashboards-provisioning-gitops-reusable-dashboard-libraries.md) into:

```text
grafana-gitops/
  dashboards/postgres.json
  dashboards/redis.json
  fixtures/manifest.json
  fixtures/degraded.json
  scripts/gitops_gate.py
  tests/test_gitops_gate.py
```

## 2. Execute

```bash
cd grafana-gitops
python3 scripts/gitops_gate.py fixtures/manifest.json .
if python3 scripts/gitops_gate.py fixtures/degraded.json .; then
  echo "FAIL: unsafe manifest accepted"; exit 1
else
  echo "PASS: unsafe manifest rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL, 24 tests PASS.

## 3. Twelve negative drills

1. Duplicate UID.
2. Invalid source path.
3. Missing owner.
4. Missing review approval.
5. Missing unit test evidence.
6. Missing cluster scope.
7. Missing tenant scope.
8. Refresh too frequent.
9. Query budget exceeded.
10. Invalid panel count.
11. Datasource UID mismatch.
12. Missing rollback revision.

Use fixture copies only. Document risk, detection, remediation and rollback.

## 4. Optional staging GitOps workflow

Create a branch, submit a PR with a dashboard change, run checks, import/provision into staging, verify source consistency and datasource reachability, and simulate reverting to a reviewed revision. Never reuse production credentials for local testing.

## 5. DBRE tabletop

A Redis dashboard revision is promoted with the wrong datasource UID and an unbounded variable, causing empty panels and expensive queries. Investigate Git desired state, live Grafana state, backend query load and RBAC; revert the dashboard and document change evidence.

## 6. Evidence

```text
UTC / operator:
Manifest and Git revision:
Dashboard UIDs / datasource UID:
Healthy/degraded gate / 24 tests:
12 negative drills:
Optional staging import / rollback:
RCA / reviewer / score:
```

**Acceptance:** 24 tests pass, degraded manifest rejected, dashboard source UIDs match manifest and promotion/rollback ownership is documented.
