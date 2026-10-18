# Chapter 085 — Executable Multicloud Inventory Project

This directory contains **real standalone Python source files** rather than code blocks that must be extracted from a tutorial.

- \`inventory.py\`: bounded AWS EC2, Azure ARM and GCP project inventory adapters with dependency injection, offline fake SDKs and dry-run CLI.
- \`live_inventory.py\`: optional, explicit \`--allow-live\` read-only SDK calls using boto3, Azure Resource Management and Google Cloud Resource Manager v3.
- \`test_inventory.py\`: 17 credential-free unit tests for pagination, schema validation, deduplication, partial inventory and dry-run.
- \`requirements.txt\`: SDK dependency ranges for optional live mode.

## Local offline validation

\`\`\`bash
python3 -m venv .venv
. .venv/bin/activate
python -m compileall -q inventory.py live_inventory.py test_inventory.py
python -m unittest -v test_inventory.py
python inventory.py --provider aws --dry-run
python inventory.py --provider aws --max-records 1
python inventory.py --provider azure
python inventory.py --provider gcp
python live_inventory.py --provider aws --scope us-east-1
\`\`\`

The last command is **still a dry-run** because \`--allow-live\` is omitted. The offline suite uses no third-party dependencies or cloud credentials.

Windows PowerShell: \`py -3 -m venv .venv\`, \`.venv\\Scripts\\Activate.ps1\`, \`py -m unittest -v test_inventory.py\`.

## Optional approved live inventory

Only after obtaining an approved read-only identity and verifying target account/subscription/project scope:

\`\`\`bash
python -m pip install -r requirements.txt
python live_inventory.py --provider aws --scope us-east-1 --max-records 100 --allow-live
python live_inventory.py --provider azure --scope 00000000-0000-0000-0000-000000000000 --max-records 100 --allow-live
python live_inventory.py --provider gcp --scope 123456789 --max-records 100 --allow-live
\`\`\`

Replace placeholders with **authorized** scopes. AWS uses the active boto3 credential chain, Azure uses \`DefaultAzureCredential\`, and GCP uses Application Default Credentials. The project does not assume permission to enumerate organizations. **GCP enumerates projects, not Compute Engine VMs**. Provider calls and credentials are not exercised in the default test suite. Verify identity and API permissions before live execution.

## Operational limitations

- \`max_records\` is a memory bound; reaching it while more unique records exist sets \`partial=true\`.
- The live script intentionally suppresses detailed provider exceptions to avoid accidental secret exposure. Use approved provider audit logs for root-cause analysis.
- The lab relies on provider SDK retry policies and serial pagination; it does not implement independent application backoff or persistent checkpoints.
- Azure and GCP SDK pagination is delegated to SDK iterators. AWS uses a paginator.
- Live results are read-only, not a complete organization inventory; scope, permissions and eventual consistency apply.
- Avoid running in production until SDK versions, quotas, endpoint/TLS settings, identity and telemetry are reviewed.

## Validation status

Files are published. The Python unit tests, live cloud integration, security review and CI pipeline **have not been run by publication**. A test result must be recorded only after independent execution.
