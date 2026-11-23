# Lab 002 — Read-Only CLI, Context and RBAC Verification

**Target:** Authorized OCP 4.x cluster, matching `oc` CLI, non-privileged identity. **Status:** Not executed.

## Procedure (Windows PowerShell or Bash)

1. Verify trusted CLI installation: `oc version --client`.
2. Log in interactively to the approved API: `oc login https://api.example.com:6443` (replace with the approved endpoint; do not supply a password or token on the command line).
3. Confirm identity and destination: `oc whoami`, `oc whoami --show-server`, `oc config current-context`, `oc project -q`.
4. Confirm version: `oc version` and compare the client/server minor versions against your supported policy.
5. For an approved namespace, execute `oc auth can-i get pods -n <approved-project>` and `oc auth can-i list deployments -n <approved-project>`.
6. Check cluster-scoped authorization: `oc auth can-i get nodes`. A result of `no` is acceptable for a namespace-only identity.
7. If authorized, execute `oc get pods -n <approved-project>`. Do not modify any objects.
8. Open the organization's approved console and confirm the same user and project. Optionally use `oc whoami --show-console`.
9. Record the previous context if changed and restore it with `oc config use-context <previous-context>` after verifying the intended mapping.

## Expected observations

- The client reports its version; the server version appears only with a working connection and authorization.
- The current context, API endpoint and identity match the authorized environment inventory.
- `can-i` returns `yes` or `no`; denied access is documented, not bypassed.
- Namespace read succeeds only if RBAC permits it.
- The console respects the same access policy.

## Evidence template (fill only after real execution)

| Field | Result |
| --- | --- |
| UTC timestamp | Not run |
| Sanitized environment and approved endpoint identity | Not run |
| Client and server versions | Not run |
| User identity (sanitized) and context verified | Not run |
| Namespace-scoped RBAC outcome | Not run |
| Cluster-scoped RBAC outcome | Not run |
| Console navigation verified | Not run |
| Failures and remediation tickets | Not run |
| Reviewer | Pending |

Never attach `oc config view --raw`, kubeconfig files, login tokens, passwords or unredacted screenshots.

**Pass gate:** All performed checks match the expected environment, denied permissions are documented, no cluster resources changed, and reviewer confirms sanitized evidence. **Current outcome: untested.**

See [Chapter 002](../chapters/002-ocp-cli-console-and-access.md).
