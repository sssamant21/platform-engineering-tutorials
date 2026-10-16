# Chapter 057 — Hands-on Lab: Jenkins RBAC, Folder Security and Least Privilege

**Environment:** Disposable Jenkins LTS controller, Role Strategy or Matrix Authorization plugin, JCasC, test users/groups, optional Kubernetes agents. Do not alter production roles.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Inventory | Record Jenkins and authorization plugin versions | Baseline |
| 02 | Threat model | Map roles and trust boundaries | Diagram |
| 03 | Personas | Define admin, auditor, developer, operator | Matrix |
| 04 | Folders | Create team-a/team-b/production lab folders | Tree |
| 05 | IdP groups | Map test identities/groups | Mapping |
| 06 | Global roles | Restrict Overall/Administer | Export |
| 07 | Item role | Grant team-a Job/Read | Access |
| 08 | Build role | Grant team-a Job/Build | Allowed |
| 09 | Negative test | Deny team-a access to team-b | Denied |
| 10 | Production | Deny developer Job/Configure | Denied |
| 11 | Replay | Deny developer Run/Replay | Denied |
| 12 | Auditor | Grant read-only visibility | Allowed |
| 13 | Anonymous | Deny private folder discovery | Denied |
| 14 | Regex | Test folder name collision | Result |
| 15 | JCasC | Export/validate role configuration | YAML |
| 16 | Credentials | Scope lab secret to trusted folder | Scope |
| 17 | Pipeline | Test safe credential binding | Build |
| 18 | Agent RBAC | Deny Kubernetes secret listing | `can-i` |
| 19 | Access review | Compare approved/effective grants | Report |
| 20 | Sign-off | Complete least-privilege acceptance | Review |

## 12 troubleshooting drills

1. Missing Overall/Read prevents navigation.
2. Item role pattern matches unintended folder.
3. Developer can configure production Pipeline.
4. Run/Replay granted on sensitive release job.
5. Folder credential available to untrusted Pipeline.
6. Group claim missing after SSO login.
7. Service account retains dormant privileges.
8. JCasC role schema invalid.
9. Authorization plugin upgrade changes behavior.
10. Anonymous can discover private job.
11. Build agent can list Kubernetes Secrets.
12. Administrator locked out by incorrect role mapping.

Use test identities and a disposable controller. Mark unavailable plugin/IdP exercises blocked, not passed.

## Commands

```sh
kubectl auth can-i list secrets -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-build
kubectl auth can-i create deployments -n production \
  --as=system:serviceaccount:jenkins-build:jenkins-build
```

Both should be denied for ordinary build identities. Substitute actual lab namespaces and service accounts.

## Evidence template

```text
UTC timestamp:
Jenkins core/plugin versions:
Security realm:
Authorization strategy:
Test identities/groups:
Global role matrix:
Folder role patterns:
Allowed access results:
Denied access results:
Credential scope:
JCasC export validation:
Agent/Kubernetes RBAC:
Break-glass recovery:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or marked blocked.
- [ ] Admin grants limited to approved principals.
- [ ] Team folders isolated with negative tests.
- [ ] Production Job/Configure and Replay restricted.
- [ ] Credential scope verified with trusted/untrusted jobs.
- [ ] Kubernetes build SA cannot list Secrets.
- [ ] JCasC validated on disposable controller.
- [ ] Access review and recovery procedures documented.
- [ ] Reviewer signs off.

**Related:** [Chapter 057 — Jenkins Role-Based Access Control, Folder Security and Least Privilege](../057-jenkins-rbac-folder-security-least-privilege.md).
