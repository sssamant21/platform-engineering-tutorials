# V06 — Offline regression execution and evidence protocol

**Status:** Authored, not executed. **Scope:** `openshift/` only. No real OpenShift API access is required or authorized by this protocol.

## Preconditions

- Use a clean, disposable checkout of the existing draft PR branch; verify `git status --short` and `git rev-parse HEAD` and record the commit SHA.
- Python 3.10+; Bash available for Bash mock tests; PowerShell 7 (`pwsh`) required for PowerShell mock tests. On Windows, use Git Bash or WSL for the Bash suite, and PowerShell 7 for the PowerShell suite.
- Run without real cluster credentials. Set `KUBECONFIG` to a nonexistent path inside a disposable test environment, and ensure no production access is needed. Merely unsetting `KUBECONFIG` is insufficient because a real `oc` may then use the default `$HOME/.kube/config`. The Bash suite uses a temporary mock executable; the PowerShell suite uses a session-local mock function. Do not execute extracted worksheet scripts directly outside these harnesses. The tests provide mock `oc` implementations and temporary credentials paths; never replace those mocks with a real client.
- Do not paste real kubeconfig, tokens, user identities, cluster endpoints, or secrets into issue/PR evidence.


## Mandatory mock-only execution guard

Before running any suite, use a **disposable shell or CI runner** with no production kubeconfig mounted. These tests are intended to execute extracted worksheet code only through their mocks. An isolated `KUBECONFIG` is a defense-in-depth control, **not** a replacement for verifying that the mocks intercept every `oc` invocation.

On Linux or Git Bash, in the disposable shell:

```sh
export KUBECONFIG="$(mktemp -d)/nonexistent-kubeconfig"
python -c 'import os; assert os.environ.get("KUBECONFIG") and not os.path.exists(os.environ["KUBECONFIG"])'
```

On PowerShell 7, in a disposable session:

```powershell
$env:KUBECONFIG = Join-Path ([System.IO.Path]::GetTempPath()) ("ocp-offline-" + [guid]::NewGuid().ToString() + ".yaml")
if (Test-Path -LiteralPath $env:KUBECONFIG) { throw "Refusing existing kubeconfig path" }
```

Do **not** invoke `oc whoami`, `oc version`, or any other real `oc` as a preflight; the test runner must remain offline. Review the harness source for mock interception before executing it. If interception cannot be established, classify the suite **BLOCKED** and do not run the extracted worksheet. Record the environment guard and the harness review in the evidence record. Never commit a kubeconfig, even a disposable one.

## Execution (repository root)

Run the suites separately so that a skipped PowerShell suite cannot be mistaken for a passing suite:

```sh
python -m unittest discover -s openshift/tests -p 'test_v05_bash_identity_guard.py' -v
python -m unittest discover -s openshift/tests -p 'test_v05_powershell_identity_guard.py' -v
python -m unittest discover -s openshift/validation -p 'test_*.py' -v
python openshift/validation/check_relative_links.py
```

### Result integrity gate (mandatory)

A process exit code of zero is **not sufficient evidence** that a suite ran. Python `unittest` can exit successfully when zero tests are discovered, and a suite can report `OK (skipped=N)` when its runtime dependency is absent. For each command above, preserve the complete sanitized output and check the `Ran N tests` line against the actual test definitions at the pinned commit. For the V05 identity-guard suites, the currently authored expectations are **14 Bash tests** and **14 PowerShell tests**; recount before execution if the branch has advanced. Treat `Ran 0 tests` as **BLOCKED**, not PASS. Treat missing PowerShell 7 or an entirely skipped suite as **SKIP**, not PASS, regardless of process exit status. A partial skip requires reporting both executed and skipped counts; never label the entire suite unqualified PASS.

In Bash/Git Bash, capture each exit status immediately (before any subsequent command):

```sh
python -m unittest discover -s openshift/tests -p 'test_v05_bash_identity_guard.py' -v
bash_exit=$?
printf 'Bash suite exit status: %s\n' "$bash_exit"
```

In PowerShell 7, capture the native process exit status using `$LASTEXITCODE` immediately after invoking Python; do not rely on `$?` for the numerical exit code:

```powershell
python -m unittest discover -s openshift/tests -p "test_v05_powershell_identity_guard.py" -v
$powerShellSuiteExit = $LASTEXITCODE
Write-Output "PowerShell suite exit status: $powerShellSuiteExit"
```

Do not automate a green status solely from these shell snippets: a reviewer must also reconcile the discovered count, skip details, assertions, mock interception and sanitized output. If the complete checkout is unavailable, mark all four commands **BLOCKED / NOT RUN**; do not substitute source inspection for execution.

The last command **executes** the repository's read-only local Markdown link audit (it exits nonzero for missing local targets). It does not check external URLs or anchor fragments. Use `--help` separately only to inspect options. On Windows PowerShell, use double quotes around glob patterns and `py -m unittest` if `python` is not on PATH.


### Evidence capture without masking failures

Run each command **without a pipeline** and capture stdout and stderr together in a disposable, access-controlled directory. Piping into `tee` can obscure the test runner's nonzero exit code unless shell-specific pipeline-failure handling is enabled. For example, on Bash:

```sh
mkdir -p /tmp/ocp-v06-offline-evidence
python -m unittest discover -s openshift/tests -p 'test_v05_bash_identity_guard.py' -v > /tmp/ocp-v06-offline-evidence/bash.log 2>&1
bash_exit=$?
printf 'Bash suite exit status: %s\\n' "$bash_exit"
```

On PowerShell 7, use a fresh temporary directory and native redirection:

```powershell
$evidenceDir = Join-Path ([System.IO.Path]::GetTempPath()) ("ocp-v06-evidence-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $evidenceDir | Out-Null
python -m unittest discover -s openshift/tests -p "test_v05_powershell_identity_guard.py" -v *> (Join-Path $evidenceDir "powershell.log")
$powerShellSuiteExit = $LASTEXITCODE
Write-Output "PowerShell suite exit status: $powerShellSuiteExit"
```

Keep raw logs **outside the repository** until manually inspected and sanitized. Do not commit the raw logs, environment dumps or real cluster identifiers. Record the count from the `Ran N tests` line, the number of skips, and the process exit code independently. A missing `Ran N tests` summary is **BLOCKED/ERROR**, never PASS. Delete temporary raw evidence after approved sanitized results have been retained.

## Evidence recording

Record for each suite: UTC timestamp, branch and SHA, operating system, Python/Bash/PowerShell versions, exact command, test count, PASS/FAIL/ERROR/SKIP counts, sanitized stdout/stderr, and the exit code. A missing `pwsh` means **SKIP**, not PASS. A test harness that cannot start is **BLOCKED**, not a test failure. Store sanitized evidence under `openshift/validation/evidence/` only after review; never commit temporary files containing secrets.

Expected behavior: mock identity mismatch, authorization API failure, ambiguous authorization and failed reads must stop with nonzero status without subsequent resource reads; explicit authorization denial may skip that resource. These are assertions to test, **not results**.

## Review gates

1. Any failure: reproduce against the same commit and isolate test expectation defects from actual worksheet defects; document a minimal fix and rerun the entire affected suite.
2. All offline tests passing does **not** prove OCP 4.22 command compatibility, cluster safety or production readiness.
3. Version-sensitive upgrade/etcd actions require authoritative OCP 4.22 documentation review, isolated authorized runtime validation, independent DBRE/SRE review, change approval, rollback or recovery decision points and an evidence-backed RPO/RTO assessment.
4. Do not merge the draft PR or promote the procedures to production-approved solely on offline results.

## References

- [V04 diagnostic worksheet](V04-upgrade-etcd-recovery-evidence-worksheet.md)
- [V05 identity-guard regression matrix](V05-isolated-identity-guard-regression-matrix.md)
- [Progress tracker](../PROGRESS-TRACKER.md)
- [OpenShift 4.22 documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22)
