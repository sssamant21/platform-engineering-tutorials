# Offline validation execution checklist (V08)

**Scope:** This is a reproducible operator checklist, not execution evidence. Run only on a credential-isolated local checkout of the existing draft PR branch. Do not use a production kubeconfig or run `oc` against a live cluster.

## Preconditions

1. Confirm the checkout is `sssamant21/platform-engineering-tutorials` on `docs/openshift-ch010-security-governance`; record `git rev-parse HEAD` and `git status --short` (expect no changes).
2. Remove inherited cluster credentials from the shell: on Bash use `unset KUBECONFIG`; on PowerShell use `Remove-Item Env:KUBECONFIG -ErrorAction SilentlyContinue`. Prefer an isolated OS account/container without any `~/.kube` credentials or cloud-provider credentials. Never print credential files.
3. Use Python 3.11+ and a local Bash and/or PowerShell 7 installation as applicable. Record interpreter versions. Inspect scripts before executing; run only mock/offline suites.

## Execute and record

From repository root:

```bash
python -m unittest discover -s openshift/validation -p 'test_*.py' -v
printf 'python_exit=%s\n' "$?"
```

PowerShell equivalent:

```powershell
python -m unittest discover -s openshift/validation -p 'test_*.py' -v
Write-Output "python_exit=$LASTEXITCODE"
```

Inspect `openshift/validation/` and the Chapter 015 lab for their exact current mock-suite entry points before invoking them. Do not assume test filenames or a PASS count from documentation. Execute each supported Bash/PowerShell suite with its documented offline mock setup; record the command, exit code, scenario count and any SKIP reason separately. Run the OpenShift Markdown link checker using its verified documented entry point (below). It scans `openshift/` by default and permits existing relative links to the sibling `kubernetes/` track without modifying those files. This is a local-file audit, **not** a remote URL or fragment check.

Bash:

```bash
python openshift/validation/check_relative_links.py
printf 'link_audit_exit=%s\
' "$?"
```

PowerShell:

```powershell
python openshift/validation/check_relative_links.py
Write-Output "link_audit_exit=$LASTEXITCODE"
```

Do not treat the link audit as a substitute for checking Red Hat OCP 4.22 documentation references. If either command fails, capture the sanitized diagnostics, correct the cause, and rerun both test families at the same reviewed commit.

## Acceptance and failure handling

- Record UTC timestamp, OS, interpreter versions, commit SHA, command line, exit status and sanitized summary for each test family. Store evidence only after checking it contains no tokens, kubeconfigs, API endpoints or identifiable tenant data.
- **PASS** requires an actual zero exit status and the expected assertions. **FAIL** requires nonzero exit or assertion failure. **SKIP** requires a specific missing dependency or unsupported environment. **NOT RUN** is distinct from PASS and SKIP.
- A passing offline suite validates only mock behavior and Markdown structure; it does **not** establish OCP 4.22 command semantics, live RBAC, recovery safety or production readiness.
- On failure, stop promotion, preserve sanitized minimal reproducer, open a corrective change in the same draft PR, rerun affected and regression suites, and request independent technical review.
- Stateful recovery, etcd restore, MachineConfig changes and upgrades require separate authorized isolated-cluster validation, documented rollback/recovery gates and platform-owner approval. Never rehearse destructive steps on production.

## Evidence template

| UTC time | Commit SHA | Environment | Suite/command | Cases | Exit | PASS/FAIL/SKIP/NOT RUN | Sanitized evidence location | Reviewer |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pending | Pending | Pending | Python unittest | Unknown until execution | Not run | NOT RUN | None | Pending |

**Current status:** Authored checklist only; no test execution, cluster access, independent approval or production certification is claimed.
