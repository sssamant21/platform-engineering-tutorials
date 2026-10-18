# Chapter 093 — Executable Kubernetes GitOps and Release Automation Lab

[Source](release.py) · [33 offline unit tests](test_release.py)

**Requirements:** Python 3.11+ standard library only. No kubeconfig, cloud credentials, GitOps controller or live infrastructure required.

## Run the executable lab

```bash
cd python/10-kubernetes-cloud-platform-engineering/labs/093
python -m compileall -q release.py test_release.py
python -m unittest -v test_release.py
python release.py --dry-run
python release.py --fail-canary
```

Windows PowerShell: `py -3 -m unittest -v test_release.py`.

Healthy synthetic canary: **propose-promotion**. Elevated errors and latency: **propose-rollback**. Both are *advisory only* and produce `mutations=0`, `network_calls=0`.

## Architecture

```text
Git desired revision + immutable image digest
        |
synthetic Kubernetes Deployment observed state
        |
generation/updated/available/desired comparison
        |
canary error rate + p95 latency + minimum traffic
        |
simulated approval + exact plan digest + rollback evidence
        |
promote / hold / rollback proposal (JSON, zero writes)
```

## Exercises

1. Validate a namespace, service, Git revision and immutable image digest.
2. Reject mutable image tags such as `nginx:latest`.
3. Simulate observedGeneration lag and unavailable replicas.
4. Change the observed Git revision and inspect out-of-sync results.
5. Raise canary error rate beyond 1% and inspect rollback proposal.
6. Raise p95 latency beyond 500 ms.
7. Remove canary telemetry and verify hold.
8. Reduce traffic below the minimum request count.
9. Remove simulated approval or mismatch the plan digest.
10. Mark rollback untested; confirm promotion is blocked.
11. Demonstrate deterministic idempotent release-plan output.
12. Design an approved Argo CD or Flux Git revert for an immutable image digest.

## Production extensions

- Implement **read-only** `AppsV1Api.read_namespaced_deployment` and Pod/Event diagnostics with explicit kubeconfig context and namespace.
- Query Argo CD Application or Flux Kustomization/HelmRelease status under least-privilege credentials.
- Pull canary metrics from Prometheus/OTel with freshness, baseline and sample confidence.
- Use authenticated, expiring approvals, signed Git revisions, branch protection and independently validated rollback evidence.
- Write desired-state changes through reviewed Git commits/PRs; avoid unapproved live Deployment patches.
- Enforce environment separation, change windows, rate limits, idempotency and immutable audit trails.
- Add watch/relist handling for API 410 and bounded jittered retries for 429/5xx.
- Test on an isolated staging namespace, including DB migration compatibility and SLO postconditions.

**Safety:** The published source is an offline **simulation**. It does not use the Kubernetes Python SDK, Argo CD or Flux APIs. The boolean approval flags are not production authentication.

## CI example (not enabled)

```yaml
name: chapter-093-gitops-release-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/10-kubernetes-cloud-platform-engineering/labs/093
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q release.py test_release.py
      - run: python -m unittest -v test_release.py
```

Pin reviewed GitHub Actions SHAs before enabling.

**Validation:** 33 tests passed locally against a development copy of the lab. The exact committed files, GitHub Actions CI and live Kubernetes/Argo CD/Flux integration have not been independently executed.
