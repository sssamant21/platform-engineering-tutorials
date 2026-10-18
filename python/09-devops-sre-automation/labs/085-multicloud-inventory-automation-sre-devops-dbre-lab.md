# Chapter 085 — Multicloud Inventory Automation SRE/DevOps/DBRE Lab

**Executable project:** [labs/085/README.md](085/README.md) · [inventory.py](085/inventory.py) · [live_inventory.py](085/live_inventory.py) · [test_inventory.py](085/test_inventory.py) · [requirements.txt](085/requirements.txt)

## Lab goals

Create a reusable, read-only multicloud inventory CLI for AWS EC2, Azure Resource Manager resources and GCP Resource Manager projects. Test SDK pagination and API contracts without real credentials, bound result memory, flag partial inventory, implement dry-run, and optionally exercise approved read-only cloud identities.

## Architecture

\`\`\`text
CLI -> scope validation -> dry-run / explicit --allow-live
    -> provider adapter (AWS boto3 / Azure SDK / GCP SDK)
    -> SDK paginator/iterator -> stable dedup -> max-records budget
    -> normalized JSON records + partial flag
\`\`\`

**Important:** The lab uses **three distinct inventory categories**. AWS EC2 instances, Azure ARM resources and GCP projects are not equivalent assets. Do not compare raw counts across clouds as though they represented the same resource type.

## Exercise 1 — Install and test offline

Clone the repository and change into \`python/09-devops-sre-automation/labs/085/\`.

\`\`\`bash
python3 -m venv .venv
. .venv/bin/activate
python -m compileall -q inventory.py live_inventory.py test_inventory.py
python -m unittest -v test_inventory.py
\`\`\`

Offline tests exercise mocked boto3 paginator responses, Azure paged resources, GCP project search requests, invalid scopes, malformed resource objects, duplicate pages, bounded inventory and dry-run behavior. They require no cloud SDK installations.

## Exercise 2 — Dry-run and offline inventory

\`\`\`bash
python inventory.py --provider aws --dry-run
python inventory.py --provider aws --max-records 1
python inventory.py --provider azure
python inventory.py --provider gcp
python live_inventory.py --provider aws --scope us-east-1
\`\`\`

The offline fixture returns two synthetic resources per provider. \`--max-records 1\` returns one record with \`partial=true\`. The final command performs no network call because \`--allow-live\` is absent.

## Exercise 3 — SDK and identity preflight

After verifying an approved read-only account/role, subscription/tenant or organization identity, install SDKs:

\`\`\`bash
python -m pip install -r requirements.txt
\`\`\`

For AWS, confirm the intended role/account using a separately approved STS identity check. For Azure, validate tenant, subscription and \`Reader\` role; \`DefaultAzureCredential\` may use local CLI identity if available. For GCP, confirm ADC identity and organization project-search visibility. Do not print tokens, environment variables or credential files.

## Exercise 4 — Optional live read-only scan

\`\`\`bash
python live_inventory.py --provider aws --scope us-east-1 --max-records 100 --allow-live
python live_inventory.py --provider azure --scope YOUR_APPROVED_SUBSCRIPTION_ID --max-records 100 --allow-live
python live_inventory.py --provider gcp --scope YOUR_NUMERIC_ORGANIZATION_ID --max-records 100 --allow-live
\`\`\`

These are **not** part of automated tests and must not be run against unauthorized accounts. Observe \`partial\`, record count and actual scope. SDK retries, rate limits and eventual consistency can affect completeness.

## Exercise 5 — SRE/DBRE incident drills

| # | Scenario | Expected behavior | Validation |
|---|---|---|---|
| 1 | AWS paginator spans pages | All records normalized | Automated |
| 2 | AWS malformed instance ID | Reject resource | Automated |
| 3 | Invalid AWS region | Reject scope | Automated |
| 4 | Azure paged resource listing | Normalize ARM ID/type | Automated |
| 5 | Malformed Azure resource | Reject resource | Automated |
| 6 | Empty Azure subscription | Reject scope | Automated |
| 7 | GCP search projects | Scoped request | Automated |
| 8 | Invalid GCP organization | Reject scope | Automated |
| 9 | Malformed GCP project | Reject resource | Automated |
| 10 | Duplicate resource across pages | Deduplicate | Automated |
| 11 | Record budget reached | \`partial=true\` | Automated |
| 12 | Exact record budget | \`partial=false\` | Automated |
| 13 | Zero record budget | Reject | Automated |
| 14 | AWS/Azure/GCP offline fixtures | Two synthetic records each | Automated |
| 15 | CLI dry-run | Zero network calls | Automated |
| 16 | CLI limited output | Partial flag present | Automated |
| 17 | Unknown provider | Reject | Automated |
| 18 | AWS throttling / HTTP 429 | Back off via SDK policy | Guided |
| 19 | Azure expired token | Refresh approved identity | Guided |
| 20 | GCP permission denied | Verify IAM/hierarchy | Guided |
| 21 | API 503 or DNS failure | Stop, retry within budget | Guided |
| 22 | Pagination changes mid-scan | Reconcile scan consistency | Guided |
| 23 | Sensitive tags or resource names | Redact before export | Guided |
| 24 | Cross-account misconfiguration | Halt and validate caller identity | Guided |

## Troubleshooting matrix

| Symptom | Check | Action |
|---|---|---|
| No records | scope, identity, permission | Verify target and expected visibility |
| Partial result | \`max_records\` and next pages | Re-run with approved larger budget |
| 401/403 | IAM/RBAC/ADC and tenant | Correct scoped identity; do not bypass |
| Throttling | API quota and SDK retry budget | Reduce scan rate and concurrency |
| Duplicate assets | provider-qualified resource ID | Deduplicate and record scan time |
| Credential leak | logs and shell history | Revoke/rotate and investigate |

## Operational runbooks

**Preflight:** confirm target account, subscription or organization, approved identity, scope and record budget; run dry-run first.

**Throttling:** reduce scan frequency and concurrency, respect \`Retry-After\`, and avoid layered retry storms.

**Partial inventory:** mark incomplete, record scan scope/time, schedule an approved continuation, and do not use the partial count for destructive decisions.

**Authorization incident:** halt, validate identity and least privilege, coordinate with cloud owner.

**Rollback and audit:** stop inventory jobs, preserve sanitized logs, revoke compromised credentials and revert automation via reviewed GitOps/IaC.

## CI example (not installed)

\`\`\`yaml
name: chapter-085-offline-multicloud
on: workflow_dispatch
jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/09-devops-sre-automation/labs/085
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q inventory.py live_inventory.py test_inventory.py
      - run: python -m unittest -v test_inventory.py
\`\`\`

Pin reviewed GitHub Actions SHAs before enabling. The offline suite has no cloud permissions.

## 100-point assessment

| Domain | Points |
|---|---:|
| boto3/Azure/GCP SDK adapters and identity | 25 |
| Pagination, record limits and normalization | 20 |
| Dry-run, scope control and idempotency | 15 |
| Retry/rate-limit design and failure classification | 15 |
| Automated tests and incident exercises | 15 |
| Security, troubleshooting and runbooks | 10 |
| **Total** | **100** |

**Acceptance:** score ≥90, offline tests executed independently, reviewed dependency versions, and approved read-only identity before any optional live scan. Publication does not prove tests or live integration succeeded.
