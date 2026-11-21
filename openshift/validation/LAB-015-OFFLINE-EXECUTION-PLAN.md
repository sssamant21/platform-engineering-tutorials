# Lab 015 — Offline regression execution and evidence plan

**Scope:** etcd recovery-readiness **read-only** lab. This is an execution procedure, **not evidence of execution**. It requires no OCP cluster, `oc` login, kubeconfig, cloud credentials or production access. Target review baseline: OpenShift 4.22.

## Preconditions and isolation

1. Use an ephemeral, unprivileged workstation/CI runner with Python 3, Bash and (for PowerShell coverage) PowerShell 7 (`pwsh`). Do not run as root/Administrator.
2. Check out the existing draft PR branch `docs/openshift-ch010-security-governance`; record the exact commit SHA. Do not use a privileged developer shell or a runner with cloud credentials.
3. Remove inherited `KUBECONFIG`, `AWS_*`, `AZURE_*`, `GOOGLE_APPLICATION_CREDENTIALS` and `OC_*` variables from the **runner** environment before invoking tests. Do not print or archive environment variables. The harness supplies synthetic values in specific test cases.
4. Review `validation/test_lab015_bash_mock.py`, `validation/test_lab015_powershell_mock.py` and `labs/015-recovery-read-only-readiness-audit.md` at the same commit. The tests execute code extracted from Markdown against a fake `oc`; no genuine cluster should be reachable.
5. Do not set `KUBECONFIG` or mount a home directory with kubeconfig in CI. Disable network egress where supported; treat this as a defense-in-depth recommendation, not an assertion that the harness is network-sandboxed.

## Run from repository root

Linux/macOS Bash:

```bash
python3 -m unittest discover -s openshift/validation -p 'test_lab015_bash_mock.py' -v
python3 -m unittest discover -s openshift/validation -p 'test_lab015_powershell_mock.py' -v
```

Windows PowerShell 7 (Bash suite requires Bash available on PATH):

```powershell
py -3 -m unittest discover -s openshift/validation -p 'test_lab015_bash_mock.py' -v
py -3 -m unittest discover -s openshift/validation -p 'test_lab015_powershell_mock.py' -v
```

The harnesses currently author **10 Bash** and **9 PowerShell** scenarios. A missing Bash or `pwsh` yields **SKIP**, not PASS. Windows PowerShell 5.1 compatibility is **not** established by the PowerShell 7 suite.

## Evidence to capture

Record UTC execution time, repository commit SHA, OS and architecture, Python/Bash/pwsh versions, test command, number of PASS/FAIL/ERROR/SKIP cases, process exit code, and sanitized failure tracebacks. Preserve no kubeconfig, tokens, environment dumps or actual cluster output. Capture the summary in a dated evidence file under `openshift/validation/evidence/` only after real execution. A zero exit code with skipped tests does not demonstrate those tests passed.

## Failure handling

- Any FAIL/ERROR blocks promotion of the lab's validation status. Reproduce against the same commit, fix the lab or harness, and rerun all affected suites.
- A SKIP requires recording the missing runtime and a follow-up run on an eligible host.
- If a test attempts to invoke a real `oc` binary, accesses network, or exposes a credential-like value, stop the runner, quarantine its logs and open a security review before resuming.
- No cluster execution or state-changing commands are authorized by this plan. Real-cluster validation requires separate approval, least-privilege credentials, scope and change controls.

## Acceptance boundary

Offline mock PASS proves only the tested local failure and output contracts. It **does not** prove OpenShift 4.22 API behavior, etcd recovery correctness, cluster availability, RPO/RTO, or production readiness. Those require separately recorded authorized lab evidence and independent technical approval.
