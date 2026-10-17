# Chapter 083 — Hands-on Lab: Jenkins Core, Plugin and Java Upgrade Validation

**Safety:** Use a disposable controller and a **separate copy** of Jenkins home for staging and recovery. No production upgrade, no real secrets, and never two active writers against the same writable state.

## 20 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Inventory Jenkins core, Java and plugin versions | Manifest |
| 02 | Record agent Java/remoting and cloud plugin | Matrix |
| 03 | Review supported version compatibility | Decision |
| 04 | Review plugin dependencies/security advisories | Report |
| 05 | Export JCasC and source-controlled configuration | Git SHA |
| 06 | Capture controller image digest | Manifest |
| 07 | Create consistent pre-change test backup | Backup ID |
| 08 | Verify backup checksum and key custody | Result |
| 09 | Restore backup to isolated staging home | Restore |
| 10 | Build candidate controller image | Image digest |
| 11 | Verify plugin installation resolution | Build log |
| 12 | Validate JCasC and configuration diff | Diff |
| 13 | Run login and negative RBAC checks | Evidence |
| 14 | Test synthetic credentials without disclosure | Pass/fail |
| 15 | Run SCM checkout and webhook test | Pipeline |
| 16 | Provision Kubernetes/VM agent | Agent logs |
| 17 | Run declarative/shared-library Pipeline | Build |
| 18 | Verify artifact publication and checksum | Digest |
| 19 | Simulate failed upgrade and isolated rollback | Timeline |
| 20 | Score acceptance, cleanup and obtain sign-off | Report |

## 12 failure drills

1. Unsupported Java/core pairing.
2. Missing plugin dependency.
3. Incompatible plugin minimum core.
4. JCasC removed/renamed field.
5. Credential decryption mismatch.
6. Authentication/authorization regression.
7. Kubernetes agent Pending.
8. Remoting Java mismatch.
9. Pipeline DSL regression.
10. TLS/CA trust regression.
11. Startup probe too aggressive.
12. Rollback with migrated state (simulation only; restore pre-change backup).

## Executable manifest capture

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${JENKINS_URL:?}"
: "${JENKINS_USER:?}"
: "${JENKINS_API_TOKEN:?}"
mkdir -p ./upgrade-evidence
java -version 2> ./upgrade-evidence/java-version.txt
curl --fail --silent --show-error \
  --user "$JENKINS_USER:$JENKINS_API_TOKEN" \
  "$JENKINS_URL/pluginManager/api/json?depth=1" \
  | python3 -c 'import json,sys; x=json.load(sys.stdin); print("\n".join(sorted(p["shortName"]+"="+p["version"] for p in x.get("plugins",[]))))' \
  > ./upgrade-evidence/plugins.txt
sha256sum ./upgrade-evidence/plugins.txt > ./upgrade-evidence/plugins.sha256
```

Keep evidence access restricted. Do not commit tokens, secrets or raw credential files.

## Executable manifest comparison

```python
from pathlib import Path

before = set(Path("plugins-before.txt").read_text().splitlines())
after = set(Path("plugins-after.txt").read_text().splitlines())
print("Removed or changed:", *sorted(before - after), sep="\n")
print("Added or changed:", *sorted(after - before), sep="\n")
```

Run after capturing the two files. Review changes manually; this diff does not establish compatibility.

## Diagnostic commands

```bash
kubectl -n jenkins get pods -o wide
kubectl -n jenkins get events --sort-by=.lastTimestamp
kubectl -n jenkins get pvc
kubectl -n jenkins-build get pods -o wide
```

## Rollback exercise

1. Start with a tested pre-upgrade backup and image digest.
2. Introduce an incompatible JCasC field **only in staging**.
3. Record startup failure and detect/acknowledge times.
4. Stop/fence the candidate controller.
5. Restore the pre-change backup to a **fresh separate** state volume.
6. Start the prior pinned controller image against that single volume.
7. Verify RBAC, credentials, Pipeline and artifact digest.
8. Record lost synthetic state, measured RTO/RPO and cleanup.

## Evidence template

```text
UTC / approver / lab namespace:
Before and after versions:
Plugin dependency/compatibility review:
Backup ID, checksum, state volume:
Single-writer check:
JCasC diff:
Authentication negative test:
Agent/remoting and CI tests:
Failure injected and first error:
Fencing/restore/rollback timestamps:
Synthetic CI and artifact validation:
RPO/RTO / score / COA / reviewer:
```

## Acceptance

- [ ] 20 exercises attempted and evidenced.
- [ ] 12 drills completed or explicitly blocked.
- [ ] Supported version compatibility reviewed.
- [ ] Pinned image and plugin manifest recorded.
- [ ] Pre-change backup integrity verified.
- [ ] Restore to separate state successful.
- [ ] Security and critical Pipelines validated.
- [ ] Rollback tested without shared writable home.
- [ ] RTO/RPO and state reconciliation documented.
- [ ] Reviewer sign-off recorded.

**Related:** [Chapter 083 — Jenkins Core, Plugin and Java Upgrades with Compatibility Testing and Rollback](../083-jenkins-core-plugin-java-upgrades-compatibility-testing-rollback.md).
