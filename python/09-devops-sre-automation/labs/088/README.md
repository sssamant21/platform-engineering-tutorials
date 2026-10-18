# Chapter 088 — Executable Incident Response and Safe Remediation Lab

**Files:** [incident.py](incident.py) · [test_incident.py](test_incident.py). Uses Python 3.11+ standard library only.

## Safety boundary

The only \`--apply\` operation creates an idempotent marker file in a local sandbox. No Kubernetes API, database, cloud service, network connection, subprocess, restart or deletion is performed. The approval flags **simulate** a gate and are **not proof of identity or authorization**. Do not adapt this directly to production writes.

## Lab 1 — Offline tests and dry-run

\`\`\`bash
cd python/09-devops-sre-automation/labs/088
python -m compileall -q incident.py test_incident.py
python -m unittest -v test_incident.py
python incident.py --incident INC-1001 --service postgres-health
\`\`\`

The last command produces a JSON dry-run plan and plan digest. It does not write a marker or audit file.

Windows PowerShell: \`py -3 -m unittest -v test_incident.py\`.

## Lab 2 — Controlled sandbox-only apply

Create an empty disposable directory first:

\`\`\`bash
mkdir -p sandbox
python incident.py --sandbox sandbox
\`\`\`

Copy the \`plan_digest\` from the dry-run. Approval expiry must be a Unix timestamp within one hour of execution. For a cross-platform command that avoids manual time calculation:

\`\`\`bash
python - <<'PY'
import time
from pathlib import Path
from incident import Plan,execute,ALLOWED_ACTION
root=Path("sandbox")
plan=Plan("INC-1001","postgres-health",ALLOWED_ACTION,"disk-pressure")
result=execute(plan,root,apply=True,approval_digest=plan.digest(),
               approver="oncall",approval_expires=time.time()+300)
print(result)
print(execute(plan,root,apply=True,approval_digest=plan.digest(),
              approver="oncall",approval_expires=time.time()+300))
PY
\`\`\`

The first call creates a sandbox marker; the second returns \`already-applied\`. Inspect \`sandbox/audit.jsonl\` and the marker. Never point \`--sandbox\` at a sensitive or shared directory.

## Lab 3 — Approval and idempotency failure drills

- Remove approval: apply must be rejected.
- Change one plan field after obtaining its digest: approval mismatch must be rejected.
- Expire approval: reject.
- Change the rationale but reuse incident/service marker: idempotency conflict.
- Corrupt the marker: fail closed rather than retry.
- Supply a path-like service name: reject.
- Supply stale diagnostic evidence: reject.
- Retry an identical approved operation: no duplicate marker.

## Lab 4 — Correlation and audit

The synthetic diagnostics report disk 94%, error rate 1%, CPU 38%; the deterministic rule proposes \`disk-pressure\`. This is a hypothesis, not proof of causality. Audit logs include plan digest, incident ID, actor reference and action status, but no diagnostic secrets. A real implementation must use a tamper-evident centralized audit system.

## Production extension checklist

- Authenticated approvals bound to signed plan digests, scope and expiry.
- Policy-as-code with service/environment/action allowlists and separation of duties.
- SQLite/PostgreSQL operation ledger with unique idempotency keys and transactional claims.
- Reconcile ambiguous external side effects before retry.
- Rate limits, bounded deadlines, fencing, distributed leases and emergency stop.
- Secret-safe diagnostic adapters for Kubernetes, PostgreSQL, Elasticsearch and cloud APIs.
- Immutable audit evidence, SLO-based postcondition checks, and rehearsed rollback.
- Test against disposable infrastructure only, with explicit owner authorization.

## CI template (not installed)

\`\`\`yaml
name: chapter-088-incident-safety
on: workflow_dispatch
jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/09-devops-sre-automation/labs/088
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q incident.py test_incident.py
      - run: python -m unittest -v test_incident.py
\`\`\`

Pin reviewed action commit SHAs before enabling. Tests use only temporary directories.

**Validation:** Source and tests are published. Execution of the final GitHub version and CI is pending. A simulated approval is not production authorization.
