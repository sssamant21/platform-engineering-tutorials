# Offline validation execution checklist (V08)

**Scope:** This is a reproducible operator checklist, not execution evidence. Run only on a credential-isolated local checkout of the existing draft PR branch. Do not use a production kubeconfig or run `oc` against a live cluster.

## Preconditions

1. Confirm the checkout is `sssamant21/platform-engineering-tutorials` on `docs/openshift-ch010-security-governance`; record `git rev-parse HEAD` and `git status --short` (expect no changes).
2. **Credential isolation is mandatory:** clearing `KUBECONFIG` alone is insufficient because `oc`/`kubectl` can fall back to the default kubeconfig under the user home directory. Use a disposable unprivileged OS account or isolated container with an empty home directory, no mounted kubeconfig, no cloud credentials and no production network access. Confirm the home directory contains no `.kube/config` before running any mock script; do not display or copy credential contents. On Bash, `unset KUBECONFIG`; on PowerShell, `Remove-Item Env:KUBECONFIG -ErrorAction SilentlyContinue`. Do not assume an environment-variable change removes other credential sources.
3. Review every mock script for subprocess calls, network access and environment inheritance before execution. If a mock could invoke a real `oc`, `kubectl`, cloud CLI or network endpoint, **STOP** until isolation is independently verified. Never rely on PATH shadowing alone as a security boundary.
4. Use Python 3.11+ and a local Bash and/or PowerShell 7 installation as applicable. Record interpreter versions. Inspect scripts before executing; run only mock/offline suites.

## Scope and change-boundary gate

Before testing or preparing the draft PR for review, inspect the actual diff against the target branch. Do **not** infer the target branch from the checkout name. For the current PR targeting `main`, use:

```bash
git fetch origin main
git diff --name-only origin/main...HEAD
git diff --check origin/main...HEAD
```

PowerShell 7 uses the same three Git commands. Record their exit codes and the changed-path inventory. Every changed path must begin with `openshift/`, except a minimal root `README.md` navigation change. Any `kubernetes/` or `data-platform-engineering-tutorials/` change is a **STOP** condition, not an acceptable warning. Inspect the actual root README diff if present. Do not run a force-push or merge as a response to a failed gate. If `git fetch` fails, mark the comparison **BLOCKED**, rather than silently comparing against a stale local main.


For a machine-checkable, fail-closed path allowlist (after a successful fresh fetch), run `python openshift/validation/check_pr_scope.py --base origin/main` from the repository root and record its exit code. Exit 0 checks path scope only; exit 1 indicates unexpected paths; exit 2 means BLOCKED or root README manual review required. This check does not replace `git diff --check`, full content review, or tests. The script does not fetch `main` itself, so a stale base is not detected automatically.

Inspect the diff for credential-like material, internal API URLs, tenant identifiers, and unsafe state-changing commands. A clean `git diff --check` verifies whitespace only; it does **not** certify security or documentation correctness. Preserve sanitized evidence of the file list and review outcome.

## Offline-only safety preflight

Before executing any harness, record a sanitized confirmation that the disposable account/container has no kubeconfig, no cloud credentials and no route to production control-plane endpoints. Never run `oc whoami` or any other live cluster probe merely to prove isolation. If the preflight cannot be established, mark all mock executions **BLOCKED / NOT RUN** and perform static source review only. This prevents accidental live access when a test unexpectedly falls through to a real CLI.

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
printf 'link_audit_exit=%s\n' "$?"
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
