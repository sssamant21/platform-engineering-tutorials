# Chapter 062 — Hands-on Lab: Jenkins Configuration as Code Architecture and Automation

**Environment:** Disposable Jenkins LTS Docker/Podman controller, Configuration as Code plugin, Git, Python/PyYAML, synthetic test identities and credentials. Do not apply to production.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Inventory | Record core/plugin versions | Baseline |
| 02 | Architecture | Diagram JCasC/Git/secret trust | Diagram |
| 03 | Repository | Create casc/, plugins.txt and tests/ | Tree |
| 04 | Baseline | Set controller executors to zero | YAML |
| 05 | Root URL | Configure lab location URL | YAML |
| 06 | Parse | Validate YAML syntax | Output |
| 07 | Duplicate keys | Detect conflicting YAML paths | Failure |
| 08 | Secrets | Substitute synthetic env value | Result |
| 09 | Secret scan | Reject hardcoded test token | Denied |
| 10 | Image | Build Jenkins image with plugins | Digest |
| 11 | Startup | Start disposable controller | Logs |
| 12 | Schema | Validate JCasC against plugins | Result |
| 13 | Authentication | Test lab admin login | Allowed |
| 14 | RBAC | Deny developer admin access | Denied |
| 15 | Credentials | Test synthetic scoped secret | Build |
| 16 | Agent | Validate lab agent connection | Status |
| 17 | Drift | Change benign UI setting | Diff |
| 18 | Reconcile | Restore Git-approved config | Result |
| 19 | Rollback | Inject invalid JCasC and recover | RTO |
| 20 | Review | Sign off acceptance and handover | Report |

## 12 troubleshooting drills

1. YAML parse failure.
2. Duplicate JCasC configuration key.
3. Unknown plugin attribute.
4. Missing secret substitution.
5. Authorization lockout.
6. Wrong Jenkins root URL.
7. Plugin dependency mismatch.
8. Missing Pipeline step.
9. Credential scope mismatch.
10. Kubernetes agent template failure.
11. Unreviewed UI configuration drift.
12. Rollback from incompatible config.

## Commands

```sh
python3 -c 'import glob,yaml; [yaml.safe_load(open(p)) for p in glob.glob("casc/*.yaml")]'
docker build -t jenkins-jcasc-lab:ch062 .
docker image inspect jenkins-jcasc-lab:ch062 --format '{{.Id}}'
```

YAML parsing alone does **not** validate JCasC plugin schema or duplicate mapping keys. Use a duplicate-key-aware linter and start an isolated controller with the installed plugin set.

## Evidence template

```text
UTC timestamp:
Jenkins core/plugin versions:
JCasC Git SHA:
Controller image digest:
Secret source and scope (no values):
YAML/schema validation:
Auth/RBAC negative tests:
Agent/Pipeline smoke tests:
Drift detected:
Failure injected:
Rollback duration:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or marked blocked.
- [ ] No plaintext secrets in Git.
- [ ] JCasC validated against installed plugins.
- [ ] Controller starts with reviewed configuration.
- [ ] Negative RBAC tests pass.
- [ ] Drift and rollback demonstrated.
- [ ] Reviewer signs off.

**Related:** [Chapter 062 — Jenkins Configuration as Code (JCasC) Architecture and Automation](../062-jenkins-configuration-as-code-jcasc-architecture-automation.md).
