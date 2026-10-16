# Chapter 035 — Enterprise SCM Integration Reliability Capstone Lab

**Scope:** Disposable Jenkins controller, isolated agents, GitHub test repository and GitLab test project. No production secrets or privileged fork builds.

## Preparation

Create both SCM fixtures with protected `main`, test feature branch, PR/MR, `README.md`, `Jenkinsfile` and executable `ci/test.sh`. Configure a GitHub Branch Source job and a GitLab Branch Source job (or a GitLab-plugin Pipeline from SCM, documenting differences). Record controller/plugin versions, credential IDs, agent labels and starting SHAs.

## 20 capstone exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Architecture | Diagram provider → proxy → Jenkins → agent | Trust boundary map |
| 02 | Plugin inventory | Record core, Git, GitHub and GitLab plugins | Compatibility record |
| 03 | SCM identities | Review GitHub App and GitLab token scopes | Least-privilege sign-off |
| 04 | Protected branches | Configure main review rules in fixtures | Policy evidence |
| 05 | GitHub discovery | Run branch source indexing | Branch and PR jobs |
| 06 | GitLab discovery | Run chosen integration scan/trigger | Branch and MR evidence |
| 07 | GitHub checkout | Build fixture and record HEAD | Exact SHA |
| 08 | GitLab checkout | Build fixture and record HEAD | Exact SHA |
| 09 | GitHub webhook | Deliver push event | Delivery ID → build |
| 10 | GitLab webhook | Deliver push event | Delivery ID → build |
| 11 | GitHub PR | Test origin PR head/merge strategy | Selected SHA |
| 12 | GitLab MR | Test origin MR head/merge strategy | Selected SHA |
| 13 | Status reporting | Verify supported publishers | Result on tested SHA |
| 14 | Fixture failure | Break `ci/test.sh` | Build/status fails |
| 15 | Fork trust | Review external PR/MR configuration | Secrets isolated |
| 16 | Duplicate event | Redeliver safe webhook | No unsafe side effects |
| 17 | Credential outage | Revoke test credential | Fail-closed result |
| 18 | Rotation | Replace scoped credential | Verified recovery |
| 19 | Indexing incident | Narrow discovery/scan cadence | Stable scan behavior |
| 20 | Rollback and scoring | Restore baseline integration config | Successful build and rubric |

## 15 troubleshooting drills

1. GitHub App installation removed from fixture repo.
2. GitLab token expired or wrong scope.
3. Incorrect GitHub webhook URL.
4. Incorrect GitLab plugin-specific webhook URL.
5. Webhook secret mismatch.
6. Reverse proxy returns 403/404.
7. HTTP 2xx webhook but no branch indexing.
8. Missing PR discovery trait.
9. Missing MR discovery trait.
10. Head/merge SHA mismatch.
11. GitHub/GitLab API rate limit.
12. Duplicate webhook and polling triggers.
13. Isolated agent offline.
14. Fork PR/MR privilege boundary.
15. Orphaned branch retention misconfiguration.

For each drill record symptom, provider delivery, Jenkins indexing/build log, expected SHA, actual SHA, root cause, corrective action and retest. Mark unsafe/unavailable drills blocked with explanation.

## Fixture script

```sh
#!/bin/sh
set -eu
test -f README.md
test -f Jenkinsfile
mkdir -p evidence
git rev-parse HEAD > evidence/scm-revision.txt
printf 'SCM fixture PASS\n'
```

Use `chmod +x ci/test.sh` and commit it to each test repository.

## Evidence template

```text
UTC time:
Jenkins core and plugin manifest:
GitHub fixture repository / PR:
GitLab fixture project / MR:
Credential IDs (never values):
Webhook delivery IDs and HTTP statuses:
Branch discovery and scan duration:
Expected SHAs:
Actual checkout SHAs:
Status/check contexts and results:
Agent label/image:
Failure injection and root cause:
Recovery time:
Rollback verification:
Reviewer:
```

## Final 100-point assessment

| Category | Points |
|---|---:|
| Architecture and governance | 15 |
| Credential isolation and trust | 15 |
| GitHub integration | 15 |
| GitLab integration | 15 |
| Provenance/status/audit | 10 |
| Observability and SLOs | 10 |
| Failure injection | 10 |
| Recovery and handover | 10 |
| **Total** | **100** |

Pass at **85+** only if critical security and recovery gates also pass.

## Acceptance checklist

- [ ] All 20 exercises attempted and documented.
- [ ] All 15 drills completed or explicitly blocked.
- [ ] Both SCM providers have verified checkout provenance.
- [ ] Webhook events correlate to builds and statuses.
- [ ] PR/MR trust and credential isolation reviewed.
- [ ] Credential rotation and rollback demonstrated.
- [ ] Evidence archived and score reviewed.
- [ ] No production systems or secrets used.

**Related:** [Chapter 035 — SCM Integration Reliability Capstone](../035-scm-integration-production-operations-reliability-capstone.md).  
**Next:** Chapter 036 — Jenkins Build Automation with Maven, Gradle and npm.
