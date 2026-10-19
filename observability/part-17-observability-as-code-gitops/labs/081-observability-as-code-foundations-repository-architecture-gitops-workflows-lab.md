# Chapter 081 — Observability as Code and GitOps Foundations Lab

**Part 17 — Observability as Code and GitOps**

## Offline validation

Copy `healthy.json`, `gitops_gate.py` and `test_gitops_gate.py` from [Chapter 081](../081-observability-as-code-foundations-repository-architecture-gitops-workflows.md).

```bash
python3 gitops_gate.py healthy.json
python3 -m unittest -v test_gitops_gate.py
```

Expected PASS and 28 authored tests. Capture actual output.

## Staging lab

1. Create the reference repository folder structure and CODEOWNERS.
2. Add a sample PrometheusRule and Grafana provisioning YAML.
3. Define separate lab, staging and production overlays.
4. Pin dependency versions and configure secret references.
5. Run YAML and rule checks in CI.
6. Review metric label cardinality and sensitive data exposure.
7. Open a peer-reviewed pull request with evidence.
8. Reconcile a pinned revision in isolated staging.
9. Verify scrape targets, dashboard queries and alert routing.
10. Demonstrate a safe Git revert and record drift/rollback evidence.

## Negative drills

Reject unreviewed changes, missing ownership, unsafe environment, unpinned artifacts, plaintext secrets and missing CI controls.

## Evidence worksheet

```text
Repository / owner / change ID:
Pinned artifacts:
Policy and secrets scan:
Prometheus / Grafana / Loki / Tempo / OTel:
CI results:
Staging reconciliation:
SLO and paging verification:
Drift and rollback:
Offline gate and 28 tests:
```

Synthetic manifest validation does not demonstrate a real GitOps deployment.
