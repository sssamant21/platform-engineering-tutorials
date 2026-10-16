# Chapter 065 — Hands-on Capstone: Jenkins Plugins, JCasC and Configuration Governance

**Environment:** Disposable Jenkins LTS controller, pinned plugin manifest, JCasC, Job DSL, protected Git, synthetic credentials and isolated agents. Never use production secrets or production Jenkins home.

## 20 capstone exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Architecture | Diagram controller configuration flow | Diagram |
| 02 | Baseline | Inventory core/Java/plugins | Inventory |
| 03 | Plugin lock | Create approved plugin manifest | Git |
| 04 | Image | Build controller image | Digest |
| 05 | JCasC | Apply modular YAML | Startup |
| 06 | Secret source | Substitute synthetic credential | Audit |
| 07 | Validation | Check JCasC schema | Result |
| 08 | Security | Verify admin/developer RBAC | Matrix |
| 09 | Seed | Run protected Job DSL seed | Logs |
| 10 | Idempotency | Run seed twice | Diff |
| 11 | Removal | Validate IGNORE deletion policy | Preserved |
| 12 | SCM | Verify generated Pipeline branch | Build |
| 13 | Agents | Validate least-privilege build agent | RBAC |
| 14 | Policy | Reject insecure configuration | Denied |
| 15 | Promotion | Record Git SHA and image digest | Record |
| 16 | Drift | Inject benign UI change | Alert |
| 17 | Security drift | Simulate unauthorized role change | Alert |
| 18 | Reconcile | Restore reviewed desired state | Result |
| 19 | Recovery | Restore known-good image/config | RTO |
| 20 | Assessment | Complete scorecard and handover | Sign-off |

## 20 troubleshooting drills

1. Missing plugin dependency.
2. Plugin/core version mismatch.
3. Plugin security advisory.
4. Invalid JCasC YAML.
5. Unknown JCasC attribute.
6. Missing secret substitution.
7. Duplicate JCasC key.
8. Unauthorized admin grant.
9. Seed permission denied.
10. Unsupported Job DSL method.
11. Unexpected job deletion.
12. Untrusted PR secret access.
13. Excess agent Kubernetes RBAC.
14. Manual UI drift.
15. Image digest mismatch.
16. Missing Pipeline step after plugin upgrade.
17. JCasC reload failure.
18. Update center outage.
19. Backup missing encryption keys.
20. Emergency change not reconciled.

Run drills only on isolated synthetic state. Mark unsupported integrations **blocked**, not passed.

## Sample commands

```sh
jenkins-plugin-cli --version
docker build -t jenkins-config-capstone:ch065 .
docker image inspect jenkins-config-capstone:ch065 --format '{{.Id}}'
kubectl auth can-i list secrets -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-build
```

The plugin CLI runs where installed (usually inside Jenkins image). Replace Kubernetes namespace/service account with lab values; ordinary build identities should not list Secrets.

## Evidence template

```text
UTC timestamp:
Jenkins core/Java/plugin versions:
Git configuration revision:
Controller image digest:
JCasC schema validation:
Seed job inventory/idempotency:
Auth/RBAC negative tests:
Credential/agent isolation:
Policy gate results:
Drift detection and reconciliation:
Injected failure:
Rollback/restore RTO:
Score / mandatory gates:
Reviewer:
```

## 100-point scorecard

| Domain | Max |
|---|---:|
| Architecture/source of truth | 10 |
| Plugin lifecycle/dependencies | 15 |
| JCasC/secrets | 15 |
| Job DSL/seed safety | 15 |
| Security/identity | 15 |
| Policy/drift | 10 |
| Promotion/change | 10 |
| Recovery/rollback | 5 |
| Evidence/handover | 5 |
| **Total** | **100** |

Suggested pass: 85 and all mandatory controls.

## Acceptance checklist

- [ ] 20 exercises attempted and documented.
- [ ] 20 drills completed or explicitly blocked.
- [ ] No plaintext secrets in Git or evidence.
- [ ] Pinned image/plugin/JCasC baseline validated.
- [ ] Seed job idempotent and deletion-safe.
- [ ] Unauthorized privileges and secret access denied.
- [ ] Drift detected and reconciled.
- [ ] Rollback/restore tested.
- [ ] Scorecard and residual risks signed off.

**Related:** [Chapter 065 — Jenkins Plugins, JCasC and Configuration Governance Production Capstone](../065-jenkins-plugins-jcasc-configuration-governance-production-capstone.md).
