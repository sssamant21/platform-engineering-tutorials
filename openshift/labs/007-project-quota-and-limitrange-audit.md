# Lab 007 — Project Quota, LimitRange and Tenant Governance Audit

**Mode:** Read-only by default · **Target:** Authorized OCP 4.x project · **Runtime status:** Not executed

## Preflight

Confirm cluster identity with `oc whoami`, `oc whoami --show-server`, and `oc config current-context`. Identify an authorized project and record the OCP version. Never store tokens, kubeconfig or Secrets as lab evidence.

## Tasks

1. List accessible projects with `oc get projects`; choose an authorized non-sensitive project.
2. Check `oc auth can-i get resourcequotas -n <project-name>` and `oc auth can-i get limitranges -n <project-name>`. Record permission-denied outcomes.
3. Run `oc get resourcequota -n <project-name>` and `oc describe resourcequota -n <project-name>`. Compare Used/Hard values and identify any near-limit resource.
4. Run `oc get limitrange -n <project-name>` and `oc describe limitrange -n <project-name>`. Document defaults, minima and maxima, or absence.
5. Inspect `oc get networkpolicy -n <project-name>` and `oc get namespace <project-name> --show-labels`. **Do not claim tenant isolation** based only on these observations; request separate security review of RBAC, SCC and storage.
6. Use the chapter's illustrative YAML to reason about whether a two-container pod with per-container requests of 1 CPU and 2Gi memory would fit the quota and LimitRange. It exceeds the example LimitRange's 1Gi memory maximum per container, so admission should fail regardless of quota headroom.
7. Explain why a ResourceQuota with no matching LimitRange can lead to admission failures for pods missing resource requests/limits when quota tracks those resources.

## Optional isolated mutation exercise (not required for completion)

Only in a disposable project with explicit approval and RBAC, save the chapter's sample manifests locally, review them, and run `oc apply --dry-run=server -n <training-project> -f <manifest-file>`. Server dry run checks admission but does not persist resources. Actual `oc apply` and cleanup require separate approval and an identified owner. Avoid shared namespaces and existing resource names. Verify the resource did not already exist before creating anything.

## Evidence worksheet

| Field | Result |
| --- | --- |
| UTC time / sanitized cluster | Not executed |
| Client/server version | Not executed |
| Authorized project / RBAC | Not executed |
| Quota Used/Hard findings | Not executed |
| LimitRange min/max/default findings | Not executed |
| NetworkPolicy inventory | Not executed |
| Admission scenario answer | Not evaluated |
| Identified governance owner | Pending |
| Reviewer | Pending |

**Pass gate:** Recorded actual read-only observations and correct admission interpretation, with no unauthorized mutations. Documentation is not a substitute for execution evidence.
