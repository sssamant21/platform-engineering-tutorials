# Chapter 116 — Enterprise Security, Compliance and Disaster Recovery Lab

[Offline simulator](security_dr_lab.py) · [Automated tests](test_security_dr_lab.py) · [Complete SRE/DBRE lab](../116-enterprise-security-compliance-disaster-recovery-sre-dbre-lab.md)

Python 3.11+ standard library only. No cloud account, credentials, KMS, real encryption, network calls, backup/restore operations or production mutations.

## Run

```bash
cd python/12-enterprise-capstones/labs/116
python -m compileall -q security_dr_lab.py test_security_dr_lab.py
python -m unittest -v test_security_dr_lab.py
python security_dr_lab.py --dry-run
python security_dr_lab.py --failure
```

PowerShell: `py -3 -m unittest -v test_security_dr_lab.py`.

## Components

- `principal`: illustrative identity metadata and expiry validation, not authentication.
- `allowed`: role/tenant authorization matrix for read, backup plan, audit and restore proposal.
- `secret`: rotation age and encryption metadata gate, no secret values.
- `restore`: backup age/RPO, estimated restore duration/RTO, checksum, encryption, immutability, drill and approval gate.
- `supply`: artifact digest format, signature/SBOM evidence flags, critical findings and approval.
- `controls`: compliance checklist results, not certification.
- `redact`: key-based sample log redaction, not complete DLP.
- `demo`: synthetic ready and failure scenarios with zero external actions.

## Exercises

1. Model workload identity expiry and least privilege.
2. Deny cross-tenant reads and unauthorized restore proposals.
3. Check secret rotation/encryption metadata.
4. Define immutable offsite backup inventory and RPO/RTO.
5. Hold DR cutover for stale backup, invalid checksum or missing approval.
6. Require restore drill evidence before accepting a recovery plan.
7. Gate supply-chain releases on signature, SBOM and critical findings.
8. Map compliance controls to audit evidence and owners.
9. Redact sensitive sample logs and preserve incident timelines.
10. Draft PostgreSQL/MongoDB/Elasticsearch/Redis/Kafka/Snowflake DR dependencies.
11. Define writer fencing, isolated restore, reconciliation and cutover.
12. Prepare staging restore drill and production change approval.

## CI template (not enabled)

```yaml
name: chapter-116-security-dr-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/12-enterprise-capstones/labs/116
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q security_dr_lab.py test_security_dr_lab.py
      - run: python -m unittest -v test_security_dr_lab.py
```

Pin reviewed GitHub Action SHAs before enabling; this is an example, not an installed CI workflow.

**Security note:** The offline checks are metadata simulations, not authentication, signature verification, encryption or actual restore tests. Human approval and real staging drills are required.

**Validation:** Source and automated tests published; exact committed execution, CI, real cloud integrations, security review and production DR acceptance pending.
