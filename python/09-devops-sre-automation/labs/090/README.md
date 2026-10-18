# Chapter 090 — Executable DevOps/SRE Automation Production Capstone

**Standalone code:** [capstone.py](capstone.py) · [test_capstone.py](test_capstone.py). Requires only Python 3.11+ standard library.

## 1. Execute the offline test suite

\`\`\`bash
cd python/09-devops-sre-automation/labs/090
python -m compileall -q capstone.py test_capstone.py
python -m unittest -v test_capstone.py
python capstone.py --dry-run
python capstone.py --failures 0
python capstone.py --failures 20 --pressure
\`\`\`

Windows PowerShell: \`py -3 -m unittest -v test_capstone.py\`.

Expected: healthy synthetic service passes advisory readiness; 20 failed requests and resource pressure block readiness and produce an incident plan. No production access or third-party dependencies are required.

## 2. Safe sandbox apply exercise

Create a disposable directory:

\`\`\`bash
mkdir -p sandbox
python capstone.py --failures 0 --sandbox sandbox
\`\`\`

Copy the returned \`plan_digest\`. The only permitted action is writing a marker in the sandbox. Use the following self-contained Python exercise to simulate approval and idempotent retry:

\`\`\`python
import time
from pathlib import Path
from capstone import Plan,apply_marker
p=Plan("INC-1001","postgres-health","manual-review")
root=Path("sandbox")
for _ in range(2):
    print(apply_marker(p,root,apply=True,approval_digest=p.digest(),
                       approver="oncall",expires=time.time()+300))
\`\`\`

Run it from a Python REPL in this directory, or save it to a disposable local file. The first call returns \`applied\`; the second \`already-applied\`. Inspect \`sandbox/audit.jsonl\` and the marker. Remove the entire disposable sandbox when finished.

**Important:** the \`--apply\` and \`--approver\` flags are simulated controls, not authenticated production approval. The local action does **not** require a passing readiness gate because it is merely a marker; a real production executor must enforce independently verified readiness and authorization at apply time.

## 3. Incident drills

- **High burn:** increase \`--failures\` to 20; inspect SLO budget, burn and rationale.
- **Pressure:** add \`--pressure\`; inspect CPU/disk evidence and readiness.
- **Missing monitoring:** change the synthetic metric timestamp to stale; verify rejection.
- **Missing owner or rollback:** set a readiness check false; verify blocked gate.
- **Missing traffic:** pass an empty outcome list in the Python REPL; confirm unknown SLI and blocked readiness.
- **Approval mismatch:** change plan rationale but reuse an old digest; reject.
- **Duplicate action:** retry an identical plan; no second marker.
- **Conflicting plan:** same incident/service but different digest; reject.
- **Tampered marker:** corrupt marker JSON; fail closed.
- **Audit failure:** make sandbox unwritable; discuss ambiguous outcome if marker succeeds but audit append fails.

## 4. Production extension backlog

1. Authenticated inventory adapters for Kubernetes, AWS/Azure/GCP and DB services with least privilege, paging and budgets.
2. Prometheus/OTEL collection with stale-signal detection, latency SLI, multiwindow burn alerts and persistent history.
3. Policy engine requiring independently verified readiness, signed approval and separation of duties.
4. Transactional idempotency ledger, distributed leases/fencing and reconciliation of unknown external outcomes.
5. Immutable centralized audit, redaction and operational evidence retention.
6. Canary deployment, SLO postcondition verification, rollback and game-day testing.

Do not deploy this synthetic lab as a production controller.

## 5. CI example (not enabled)

\`\`\`yaml
name: chapter-090-offline-sre-capstone
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/09-devops-sre-automation/labs/090
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q capstone.py test_capstone.py
      - run: python -m unittest -v test_capstone.py
\`\`\`

Pin reviewed GitHub Actions SHAs before enabling. No secrets or network services are needed for tests.

**Validation:** Code and offline unit tests are committed; independent runtime/CI execution of the committed version is pending. Publication alone is not production certification.
