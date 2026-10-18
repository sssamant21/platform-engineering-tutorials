# Chapter 086 — Executable Kubernetes and Docker Automation Lab

**Standalone files:** [inventory.py](inventory.py) · [test_inventory.py](test_inventory.py) · [live_inventory.py](live_inventory.py) · [requirements.txt](requirements.txt)

## Run offline

\`\`\`bash
cd python/09-devops-sre-automation/labs/086
python3 -m venv .venv
. .venv/bin/activate
python -m compileall -q inventory.py live_inventory.py test_inventory.py
python -m unittest -v test_inventory.py
python inventory.py --namespace default --dry-run
python inventory.py --namespace default --max-records 2
python live_inventory.py --namespace default
\`\`\`

The default mode uses synthetic Kubernetes and Docker objects, not credentials, cluster access or Docker socket. The final command is a dry-run and makes zero API calls.

Windows PowerShell: \`py -3 -m venv .venv\`, \`.venv\\Scripts\\Activate.ps1\`, \`py -m unittest -v test_inventory.py\`.

## Optional authorized read-only inventory

\`\`\`bash
python -m pip install -r requirements.txt
python live_inventory.py --namespace approved-namespace --context approved-context --max-records 100 --allow-live
\`\`\`

For in-cluster service accounts use \`--in-cluster\` instead of \`--context\`. Docker inventory is **disabled by default**. \`--docker\` additionally requires access to a trusted local Docker daemon; Docker socket access is highly privileged. Do not enable it on a shared or untrusted host.

## Production limitations

- Kubernetes Pods and Deployments are fetched in **separate** paginated API list calls. This is not an atomic cross-resource snapshot.
- \`max-records\` caps normalized unique output and sets \`partial=true\` when more records are found. SDK page sizes still control peak response memory.
- Watch stream parsing is tested with synthetic events; a real watch reconnect/410 Gone recovery loop is a **guided design exercise**, not implemented in live mode.
- Live inventory is read-only; no rollout mutation, delete or restart APIs exist.
- Live client exceptions are intentionally redacted. For diagnosis use approved Kubernetes audit logs, events and Docker daemon logs.
- No Kubernetes cluster, Docker daemon, CI or live API tests are executed as part of publication.

## CI example (template only)

\`\`\`yaml
name: chapter-086-offline-inventory
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/09-devops-sre-automation/labs/086
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q inventory.py live_inventory.py test_inventory.py
      - run: python -m unittest -v test_inventory.py
\`\`\`

Pin reviewed action SHAs before enabling CI.
