# V07 — Lab 015 identity-guard regression cases

**Scope:** [Lab 015](../labs/015-recovery-read-only-readiness-audit.md), Bash and PowerShell. This is a **test design**, not executed test evidence. No real OpenShift cluster, credentials, or kubeconfig may be used.

## Isolation and prerequisites

- Execute only in a disposable process with an empty HOME, a deliberately nonexistent KUBECONFIG, and a PATH that resolves `oc` to a strict local mock. For PowerShell, explicitly shadow `oc` with a mock function in the isolated process and verify command resolution before execution.
- Mock only these commands: `whoami`, `config current-context`, `config view --minify -o jsonpath={.clusters[0].cluster.server}`, `version`, four `auth can-i` checks, and four corresponding `get` reads. Reject and log all other invocations.
- Set the approved expected server to `https://api.test.invalid:6443` and make the mock return this exact value for the matching case. Never obtain the expected value from the same mock kubeconfig.
- Capture ordered mock calls, exit status, stderr, and assertion results outside the repository; redact context and infrastructure identifiers before publishing.

## Test matrix

| Case | Injected condition | Required observation |
| --- | --- | --- |
| A | Expected server unset or empty | Nonzero exit/throw; zero `oc` calls |
| B | `whoami` fails | Stop; no context/server/version/auth/resource calls |
| C | Current-context lookup fails | Stop; no server/version/auth/resource calls |
| D | API-server lookup fails or returns empty | Stop; no version/auth/resource calls |
| E | API server differs from independently approved value | Stop; no version/auth/resource calls |
| F | `oc version` fails | Stop; no authorization or resource reads |
| G | All four permissions return explicit `yes` | Exactly four expected `get` reads, in documented order |
| H | One permission returns `no` | Skip only the corresponding resource read; do not elevate |
| I | Authorization returns an error or ambiguous output | Skip corresponding resource read; never treat as `yes` |
| J | A permitted `get` fails | Capture failed read; **do not report overall runtime PASS** |
| K | Mock receives an unrecognized or mutating command | Fail test; record violation; no real `oc` fallback |
| L | PowerShell `oc` mock returns nonzero but writes `yes` | Must not treat failed authorization as valid permission |

## Acceptance rules

A test suite PASS requires every intended case to be discovered and executed, no unexpected skips, no unmocked `oc` calls, and correct command ordering. An exit code of zero alone is insufficient. If an authorization check fails, the lab may continue with limited visibility, but the **evidence record must mark that resource SKIPPED/UNKNOWN**; a successful shell exit is not proof of full readiness.

**Known review item:** Lab 015 currently uses equality with `yes` for authorization checks but does not explicitly record each authorization command's exit code in its Bash and PowerShell examples. Case L and its Bash counterpart must be tested before claiming fail-closed behavior for all authorization failures. Any cluster read failure must also be surfaced in the final evidence status, even when the example shell proceeds.

## Approval and next action

Implement the above as mock-based regression tests, then run them in a credential-isolated checkout and record actual PASS/FAIL/SKIP. Review against the installed OCP version and Red Hat's [4.22 documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22). No snapshot, restore, privileged escalation, or production change is authorized by this document. Independent platform/security review and a separately approved recovery rehearsal remain required.
