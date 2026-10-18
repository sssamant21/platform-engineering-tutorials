# Chapter 091 — Executable Kubernetes API and Cloud-Native Lab

[Source](kube_lab.py) · [Offline tests](test_kube_lab.py)

## Offline first

Python 3.11+; no cluster or third-party package required:

\`\`\`bash
cd python/10-kubernetes-cloud-platform-engineering/labs/091
python -m compileall -q kube_lab.py test_kube_lab.py
python -m unittest -v test_kube_lab.py
python kube_lab.py --dry-run
python kube_lab.py
\`\`\`

Windows PowerShell: \`py -3 -m unittest -v test_kube_lab.py\`.

The fake API simulates paginated Pod inventory. Tests cover pagination, token loops, inventory limits, transient API retries, forbidden errors, Pod readiness, Deployment rollout health, watch events and 410 relist signals. All offline commands make **zero network calls and zero cluster mutations**.

## Optional live read-only inventory

Only on an approved nonproduction cluster, after selecting an explicit kubeconfig context and namespace:

\`\`\`bash
python -m pip install "kubernetes>=29,<35"
kubectl config get-contexts
kubectl auth can-i list pods -n sre-lab --context YOUR_STAGING_CONTEXT
python kube_lab.py --live --context YOUR_STAGING_CONTEXT --namespace sre-lab
\`\`\`

The optional adapter loads the chosen kubeconfig context and calls \`CoreV1Api.list_namespaced_pod\` only. It does **not** create, patch, delete, restart, or watch resources in the live cluster. Review dependencies and pin tested versions for actual deployment. Avoid production contexts, broad RBAC and disabled TLS verification.

## RBAC sample (documentation only)

\`\`\`yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: python-inventory-reader
  namespace: sre-lab
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list"]
\`\`\`

Do not apply automatically. An administrator must bind a dedicated identity after review.

## Exercises

1. Compare a healthy and pending Pod.
2. Lower the inventory object budget; verify fail-closed.
3. Simulate a repeated continuation token; verify loop detection.
4. Simulate HTTP 429 and 503; verify bounded retries.
5. Simulate HTTP 403; verify no retry.
6. Mark Deployment observed generation behind desired; verify rollout pending.
7. Reduce available replicas; verify degraded rollout.
8. Replay watch ADDED, MODIFIED, DELETED and BOOKMARK events.
9. Simulate watch HTTP 410; require relist.
10. Design production controller state, reconciliation and leader-election safeguards.

## Production gaps

This is a **read-only educational lab**, not a Kubernetes controller. Watch replay uses synthetic events; the optional live adapter does not implement a live watch. A production controller must implement authenticated RBAC review, event streaming with relist, cache reconciliation, jittered retry/deadlines, metrics, field ownership, leader election and independently approved writes.

## CI template (not enabled)

\`\`\`yaml
name: chapter-091-kubernetes-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/10-kubernetes-cloud-platform-engineering/labs/091
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q kube_lab.py test_kube_lab.py
      - run: python -m unittest -v test_kube_lab.py
\`\`\`

Pin GitHub Actions by reviewed commit SHAs before enabling. The committed code and CI have not yet been independently executed.
