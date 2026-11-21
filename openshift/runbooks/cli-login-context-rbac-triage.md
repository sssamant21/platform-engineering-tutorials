# Runbook — OpenShift CLI Login, Context and RBAC Triage

**Purpose:** Diagnose failed CLI/console access without granting unnecessary privileges or compromising credentials. **Risk:** Read-only diagnostics; interactive login modifies local kubeconfig state.

## Trigger and impact

An operator cannot log in, receives `Unauthorized`/`Forbidden`, reaches the wrong cluster, or cannot access an expected namespace.

## Prechecks

- Verify the cluster/environment and user identity through the platform inventory.
- Confirm approved network/VPN access and whether there is an ongoing API/identity-provider incident.
- Do not share tokens, passwords, kubeconfig or console session cookies.

## Read-only diagnostic sequence

```bash
oc version --client
oc config current-context
oc config get-contexts
oc whoami
oc whoami --show-server
oc auth can-i get pods -n <approved-project>
oc auth can-i get nodes
```

If `oc whoami` fails, classify the error first. A TLS x509 failure needs endpoint/CA verification; a timeout needs network/API investigation; `Unauthorized` needs supported SSO reauthentication; `Forbidden` indicates insufficient effective permissions. An invalid current context needs explicit mapping to the correct approved cluster before any query.

## Resolution boundaries

- Authentication: use `oc login https://<approved-api-endpoint>:6443` interactively or the organization's approved SSO flow. Never embed `-p` or `--token` secrets in command histories.
- RBAC: collect the specific denied resource, verb and namespace, then route a least-privilege request to the access owner. No ad hoc cluster-admin grants.
- Wrong context: stop, validate the correct context, then explicitly switch locally with `oc config use-context <approved-context>`; reverify server and user.
- Certificate failure: escalate to the certificate/PKI owner; never use `--insecure-skip-tls-verify` as a shortcut.

## Escalation packet

Record sanitized environment, UTC time, client version, API hostname classification, identity-provider used, exact *redacted* error, resource/verb/namespace denied, known changes, impact, and escalation owner.

## Rollback and validation

No cluster resources should change. If the default context was switched, restore the prior verified context; confirm `oc whoami --show-server`. Credential revocation/rotation is handled under the organization's security incident process, not by deleting local files blindly.

## References

- [Red Hat OCP 4.22 CLI](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/cli_tools/openshift-cli-oc)
- [Red Hat OCP 4.22 web console](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/web_console/index)
