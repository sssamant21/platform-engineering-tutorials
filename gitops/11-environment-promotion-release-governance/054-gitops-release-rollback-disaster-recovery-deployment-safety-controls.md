# Chapter 054 — GitOps Release Rollback, Disaster Recovery and Deployment Safety Controls

**Track:** GitLab CI/CD, Helm, GitOps & Argo CD — Enterprise Tutorial Series  
**Part 11:** Environment Promotion and Release Governance  
**Chapter:** 054 / 100  
**Audience:** Platform Engineers, SREs, Release Managers, DevSecOps, Database Reliability Engineers

> **Safety:** Run destructive and failure-injection exercises only in disposable staging clusters. A Git revert does not automatically restore databases, external state or deleted resources. Never enable automated pruning or forceful rollback against production without an approved impact assessment.

## 1. Learning objectives

After this chapter, you can:

1. Distinguish deployment rollback, configuration revert, roll-forward, and disaster recovery.
2. Select a recovery strategy based on failure mode and data compatibility.
3. Explain why Argo CD history rollback differs from GitOps source-of-truth rollback.
4. Design safe Kubernetes rollout settings, health probes, and disruption controls.
5. Handle database expand-and-contract migrations and irreversible state changes.
6. Build automated release validation, promotion holds, and recovery evidence.
7. Recover from Git, registry, Argo CD, cluster, and secret-management outages.
8. Execute production-style recovery labs with measurable RTO and RPO objectives.

## 2. Reference architecture

~~~text
Source CI -> immutable signed image -> GitOps promotion MR
                                      |
                             protected Git branch
                                      |
                                Argo CD sync
                                      |
                     Kubernetes Deployment / Service
                                      |
                    health, SLO and audit evidence
                                      |
                        Release failure detected
                                      |
                    +----------------------------+
                    |                            |
             Revert GitOps                  Roll forward
             desired state                 to fixed digest
                    |                            |
                    +-------------+--------------+
                                  |
                         validate recovery
                                  |
                         incident evidence

Backup/restore + DR runbooks are separate for stateful data and
control-plane or cluster loss.
~~~

**Core principle:** Git is authoritative for declared configuration. Kubernetes runtime state and external data systems are separate recovery domains. Restoring a Deployment spec does not restore lost database records or reverse a schema migration.

## 3. Recovery terminology and decision table

| Mechanism | Restores | Does not restore |
| --- | --- | --- |
| Git revert | Prior declared GitOps configuration | Stateful data, external side effects |
| Argo CD sync to reverted Git | Live resources toward reviewed desired state | Data changes or deleted external assets |
| Kubernetes rollout undo | Prior Deployment revision in Kubernetes | Durable Git source; Argo CD may overwrite it |
| Argo CD historical rollback | Historical application deployment when supported | Future Git auto-sync reconciliation; database state |
| Roll forward | Known defect via new reviewed artifact/config | Automatically undo previous data loss |
| Database PITR | Database to supported point in time | Other systems' independent state |
| Cluster/Argo CD DR | Control plane or workload platform state | Unbacked external data and missing Git artifacts |

**Decision rule:** prefer a reviewed GitOps revert for reversible application/configuration failures. Use roll-forward when reverting is unsafe due to schema or protocol changes. Use backup/restore for confirmed state loss, subject to recovery-point and consistency requirements.

## 4. Failure classification and blast radius

| Failure | Impact | First response |
| --- | --- | --- |
| Bad container image | Pods crash, readiness fails | Stop promotions; revert approved digest |
| Bad Helm/Kustomize values | Wrong resources or config | Revert configuration commit |
| Wrong GitOps target revision | Unintended release | Restore approved revision and audit actor |
| Broken database migration | Schema/data incompatibility | Stop writes as appropriate; DBRE-led recovery |
| Argo CD outage | Reconciliation delayed | Repair GitOps control plane |
| Registry outage | New image pulls fail | Restore registry/cache or defer rollout |
| Git provider outage | New manifest fetch fails | Restore Git access; avoid uncontrolled changes |
| Cluster failure | Workloads and API unavailable | Invoke platform DR procedure |
| Secret rotation failure | Authentication failures | Restore valid credential through secret manager |
| Accidental prune | Resources removed | Restore manifests; recover persistent data separately |

## 5. Safety controls before every production release

Use multiple independent controls:

- Protected GitOps branches, CODEOWNERS, independent approvals and signed release evidence.
- Immutable image digest, SBOM, signature and policy validation.
- Staging smoke tests, health checks and performance baselines.
- Explicit AppProject sources/destinations and Kubernetes RBAC/admission policies.
- Readiness/startup probes, resource requests and sensible rollout strategy.
- Change window, deployment freeze and rollback owner.
- Tested database compatibility and backup/restore procedures.
- Auditable release revision, observed digest and post-release SLO checks.

Argo CD sync status indicates desired/live reconciliation; it does not prove end-user functionality. Include application-level tests.

## 6. Kubernetes rollout safety

Example staging Deployment fragment:

~~~yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-web
  namespace: demo-staging
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  minReadySeconds: 10
  progressDeadlineSeconds: 180
  selector:
    matchLabels:
      app: demo-web
  template:
    metadata:
      labels:
        app: demo-web
    spec:
      terminationGracePeriodSeconds: 30
      containers:
        - name: web
          image: registry.example.internal/demo/web@sha256:REPLACE_WITH_VALID_DIGEST
          ports:
            - containerPort: 8080
          startupProbe:
            httpGet:
              path: /healthz
              port: 8080
            failureThreshold: 30
            periodSeconds: 2
          readinessProbe:
            httpGet:
              path: /readyz
              port: 8080
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8080
            periodSeconds: 10
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
~~~

The digest and endpoints are placeholders; replace with a tested image and actual health endpoints. For a rolling update, maxUnavailable: 0 helps preserve ready replica count **if sufficient cluster capacity exists**. It does not guarantee zero downtime, especially with external dependencies or bad readiness checks.

Check the effective rollout:

~~~bash
kubectl --context STAGING_CONTEXT -n demo-staging rollout status deploy/demo-web --timeout=5m
kubectl --context STAGING_CONTEXT -n demo-staging get deploy demo-web -o wide
kubectl --context STAGING_CONTEXT -n demo-staging get pods -l app=demo-web -o wide
~~~

## 7. GitOps revert versus Kubernetes rollback

**Preferred:** revert the GitOps commit containing the failed digest/configuration, merge through the approved emergency or normal workflow, and let Argo CD reconcile.

~~~bash
git log --oneline -8
git show --stat FAILED_GITOPS_COMMIT
git revert FAILED_GITOPS_COMMIT
# Open a reviewed revert MR, merge, then:
argocd app get demo-staging --refresh
argocd app diff demo-staging
argocd app sync demo-staging
argocd app wait demo-staging --sync --health --timeout 300
~~~

Use a separate working branch and follow branch protection; do not directly push a revert to protected production branches. A revert can conflict with subsequent changes; inspect the resulting diff rather than assuming the previous state is recovered.

### Why not rely on kubectl rollout undo?

~~~bash
# Staging-only emergency example, NOT the preferred GitOps workflow:
kubectl --context STAGING_CONTEXT -n demo-staging rollout history deploy/demo-web
~~~

Kubernetes rollback modifies live Deployment state; Argo CD may subsequently reconcile it back to the undesired Git state. Argo CD's own rollback operation also has restrictions with automated sync enabled. For persistent recovery, update the authoritative GitOps revision and verify convergence.

## 8. Database migration compatibility

For PostgreSQL, MongoDB, Snowflake, or any stateful dependency, application rollback must be coordinated with the data migration plan.

### Expand-and-contract pattern

1. **Expand:** add new columns/collections/indexes while preserving old application compatibility.
2. **Migrate:** backfill or dual-write with validation, throttling and observability.
3. **Switch:** deploy code reading the new schema/representation.
4. **Observe:** verify reads, writes, latency, error rates and data quality.
5. **Contract:** remove old schema only after rollback window and compatibility tests.

| Change | Rollback risk | Preferred approach |
| --- | --- | --- |
| Add nullable column | Usually low | Revert app if old schema still works |
| Rename/drop column | High | Delay destructive change until safe |
| Rebuild index | Performance/capacity | Evaluate DB-specific impact and rollback |
| Transform data irreversibly | High | Snapshot/backup and forward repair |
| Change API payload | Client compatibility | Versioned contracts and dual support |

**RPO/RTO:** Define the maximum acceptable data loss and restoration time per datastore. A database point-in-time restore can overwrite valid writes after the chosen restore point; obtain application/data-owner approval and coordinate downstream consumers before restoring.

## 9. Stateful recovery preflight

Before any production data restore:

~~~text
Incident/change ID:
Affected database, table/collection and region:
Failure time and last known-good point:
Backup/PITR availability and integrity:
Expected RPO and RTO:
Writes continuing or paused:
Replication/CDC/downstream impact:
Encryption and access prerequisites:
Restore target (isolated preferred):
Validation queries and checksums:
Cutover/failback owner:
Customer and compliance communication:
~~~

Restore to an isolated environment when possible and compare affected records before deciding on in-place cutover. Never treat a GitOps rollback as a substitute for database recovery.

## 10. Release automation safety gate

A release controller should require:

~~~text
approved GitOps commit
  AND verified immutable digest
  AND valid change window / exception
  AND staging tests passed
  AND no active release freeze
  AND destination policy authorized
  AND backup / rollback readiness recorded
  AND no conflicting release
~~~

This gate must be evaluated at the **effective deployment boundary**. If Argo CD auto-syncs, the production Git merge itself must be controlled. A separate GitLab manual job does not gate an already-merged auto-sync change.

## 11. Hands-on lab A — Revert a broken application release

**Environment:** disposable staging namespace and two known test images (healthy and deliberately unhealthy).

1. Record the healthy image digest, GitOps revision and Deployment health.
2. Promote the unhealthy digest via a staging GitOps MR.
3. Observe rollout failure and Argo CD health.
4. Create a Git revert MR restoring the healthy digest.
5. Merge through the normal staging approval path.
6. Reconcile and verify expected revision, observed image and readiness.

~~~bash
argocd app get demo-staging
argocd app history demo-staging
kubectl --context STAGING_CONTEXT -n demo-staging describe deploy demo-web
kubectl --context STAGING_CONTEXT -n demo-staging get pods -o wide
# After approved Git revert:
argocd app sync demo-staging
argocd app wait demo-staging --sync --health --timeout 300
~~~

**Pass:** recovered image digest matches the previously approved digest and the application-level smoke test succeeds. Record detection and recovery time.

## 12. Hands-on lab B — Detect a dangerous prune

Use an isolated namespace with a disposable ConfigMap and a test Application. Do **not** enable automated prune or delete persistent storage.

1. Add the ConfigMap to the staging GitOps repository and sync.
2. Remove the ConfigMap from desired state in a test branch.
3. Inspect Argo CD diff and intended deletion.
4. Require human review before any prune operation.
5. Revert the test branch or restore the resource declaration.

~~~bash
argocd app diff demo-staging
argocd app get demo-staging
kubectl --context STAGING_CONTEXT -n demo-staging get configmap
~~~

**Pass:** deletion is visible before sync and the team can identify which resources would be removed. Never use this exercise with PVCs, namespaces or production resources.

## 13. Hands-on lab C — Stateful rollback tabletop

**Scenario:** a new application version writes a new database format that the old application cannot read.

1. Identify the incompatible write and affected records.
2. Determine whether an application-only rollback is safe.
3. Design a forward-compatible reader or compensating migration.
4. Verify backup integrity and isolated restore feasibility.
5. Define write pause, CDC and downstream consistency handling.
6. Produce an approved recovery decision and rollback/roll-forward matrix.

**Pass:** the team does not revert the application blindly; the plan identifies data ownership, RPO/RTO and validation steps.

## 14. Hands-on lab D — Argo CD control-plane outage

In a disposable staging Argo CD installation:

1. Confirm at least two healthy API server replicas and available capacity.
2. Record a baseline Application revision and health.
3. Delete one verified staging API server pod.
4. Observe control-plane availability and rescheduling.
5. Confirm existing workload availability and restored API access.

~~~bash
kubectl -n argocd get deploy argocd-server
kubectl -n argocd get pods -l app.kubernetes.io/name=argocd-server -o wide
# Delete only a verified disposable staging server pod:
kubectl -n argocd delete pod VERIFIED_STAGING_SERVER_POD
kubectl -n argocd rollout status deploy/argocd-server --timeout=5m
argocd app get demo-staging
~~~

**Pass:** API access recovers within the agreed staging objective and application-serving health is measured separately. Do not claim zero downtime without observed data.

## 15. Hands-on lab E — Git or registry outage simulation

Use a reversible network control in a disposable staging environment, or a tabletop if safe isolation is unavailable.

1. Record normal Git and registry connectivity.
2. Simulate a temporary Git endpoint outage **without deleting repositories**.
3. Observe Argo CD refresh/manifest generation errors.
4. Restore connectivity and verify convergence.
5. Separately evaluate registry outage effects on existing pods versus new image pulls.

**Pass:** the team distinguishes control-plane reconciliation failures from workload-serving failures and documents the dependency recovery path.

## 16. Hands-on lab F — Recovery evidence and acceptance test

Capture:

~~~text
Release/change ID:
Failure injection ID:
Initial GitOps revision:
Initial image digest:
Failed revision and symptom:
Incident detection time:
Mitigation decision:
Approved revert or forward-fix commit:
Recovered GitOps revision:
Observed workload digest:
Readiness/smoke/SLO evidence:
Database compatibility decision:
Recovery time and objective:
Evidence references (redacted):
Reviewer:
~~~

**Pass:** evidence proves actual recovery rather than only successful execution of a sync command.

## 17. Disaster recovery architecture

| Dependency | Recovery source | Validation |
| --- | --- | --- |
| GitOps repository | Protected Git remote and backups | Expected commits/branches available |
| Argo CD config | Versioned manifests/Helm values and protected secret manager | Projects, applications and access restored |
| Cluster credentials | IAM/federation or approved secret recovery | Scoped authentication works |
| Container images | Registry replication/retention policy | Approved digests pull successfully |
| Kubernetes cluster | Infrastructure as code and cluster recovery plan | API, nodes, networking and storage healthy |
| Persistent data | DB-specific backups, PITR, snapshots | Integrity and RPO/RTO verified |
| Audit evidence | Independent retention-controlled archive | Records readable and tamper checks pass |

Recovery order depends on the incident. For a complete cluster loss, provision the target infrastructure, restore networking/IAM and secret dependencies, recover data with appropriate consistency, bootstrap Argo CD, reconcile workloads, then validate service behavior. Avoid assuming all applications can safely sync before their databases are ready.

## 18. Monitoring and rollback triggers

Define alerting on:

- Deployment unavailable replicas and rollout deadline exceeded.
- CrashLoopBackOff, ImagePullBackOff and failed readiness.
- Argo CD sync failure, repeated OutOfSync or Degraded health.
- Increased 5xx, latency, queue depth and business-transaction errors.
- Database connection failures, schema mismatch and data quality regressions.
- Kubernetes API admission denials and unauthorized deployment activity.
- Failed credential rotation, Git/registry access and control-plane availability.

Use agreed error budgets and release-specific thresholds. Automatic rollback may be suitable for stateless canaries but should not run blindly after irreversible data migrations.

## 19. Troubleshooting — twelve recovery failures

| # | Symptom | Investigation | Response |
| --- | --- | --- | --- |
| 1 | Git revert merged, pods unchanged | Argo CD revision/sync state | Refresh and reconcile approved state |
| 2 | Rollback immediately undone | Auto-sync desired state still bad | Fix Git source of truth |
| 3 | Revert has merge conflicts | Later GitOps commits | Review diff and produce safe revert |
| 4 | Healthy pods but service errors | Application/API/dependency metrics | Diagnose outside Kubernetes readiness |
| 5 | Old app crashes after rollback | Incompatible DB schema/data | Roll forward or DBRE-led recovery |
| 6 | ImagePullBackOff during recovery | Registry, digest, pull credentials | Restore artifact availability |
| 7 | Argo CD unavailable | API, Redis, controller, ingress | Restore dependency/bootstrap |
| 8 | Rollout stalls | Capacity, PDB, probes, scheduling | Correct capacity or deployment settings |
| 9 | Prune deleted resource | GitOps deletion, finalizers | Restore manifest and data separately |
| 10 | Restore exceeds RTO | Backup size, network, recovery steps | Invoke DR escalation and optimize plan |
| 11 | Data restored but downstream wrong | CDC/replay/replication lag | Reconcile consumers and checkpoints |
| 12 | Evidence incomplete | Logs expired or missing correlation | Repair independent audit collection |

## 20. Production runbook — failed release

**Trigger:** deployment health degradation, failed sync, unexpected customer errors or a policy violation after promotion.

**First actions:**

~~~bash
argocd app get APP_NAME --refresh
argocd app diff APP_NAME
argocd app history APP_NAME
kubectl --context TARGET_CONTEXT -n TARGET_NAMESPACE get deploy,pods,events
kubectl --context TARGET_CONTEXT -n TARGET_NAMESPACE describe deploy DEPLOYMENT_NAME
~~~

1. Declare the incident and record the deployed revision/digest.
2. Freeze subsequent promotions to the affected environment.
3. Determine whether the issue is application-only, configuration, infrastructure or stateful.
4. Check whether rollback is safe with current schema and data.
5. Revert reviewed GitOps state or roll forward under the approved emergency workflow.
6. Validate actual running digest, rollout, business transactions and SLOs.
7. Preserve redacted evidence and close only after the observation window.

## 21. Production runbook — GitOps control-plane disaster

1. Identify affected control-plane components and cluster blast radius.
2. Confirm workloads and databases are still operating before intervening.
3. Preserve logs and configuration revision identifiers.
4. Restore Git, registry, IAM/secret manager and Kubernetes API dependencies as needed.
5. Bootstrap Argo CD from a tested version-pinned recovery source.
6. Restore cluster registrations and AppProjects with scoped credentials.
7. Reconcile canary Applications before broad fleet synchronization.
8. Confirm desired Git revisions, observed image digests, health and audit forwarding.
9. Document recovery timing, data impact and prevention actions.

Do not bulk-enable pruning or blindly sync all Applications during disaster recovery.

## 22. Rollback and cleanup

Remove only lab-created resources after confirming context, namespace, ownership and finalizer effects. Revoke disposable credentials and restore any reversible network blocks. Preserve redacted evidence per retention requirements.

For production, every rollback requires an explicit data-compatibility decision. Keep a known-good digest and Git commit, but also a tested forward-fix path when state cannot be reversed safely.

## 23. Acceptance criteria

- [ ] Release recovery decision matrix is documented.
- [ ] GitOps revert workflow uses protected merge approvals.
- [ ] Running image digest and revision are validated after recovery.
- [ ] Rollout probes, surge/unavailable and capacity are reviewed.
- [ ] Automatic prune risk is tested in staging.
- [ ] Database expand-and-contract and irreversible migration risks are addressed.
- [ ] Backup/PITR integrity, RPO and RTO are validated for stateful services.
- [ ] Git, registry and Argo CD dependency recovery procedures are tested.
- [ ] Incident monitoring includes application SLOs, not only Kubernetes health.
- [ ] Unauthorized or unsafe recovery shortcuts are prohibited.
- [ ] Six labs have evidence, pass/fail results and owners.
- [ ] Production rollback/DR runbooks have review and sign-off.

## 24. Knowledge check

1. Why can kubectl rollout undo be temporary under Argo CD?
2. When is roll-forward safer than rollback?
3. Why does a Git revert not restore deleted database records?
4. What does maxUnavailable: 0 protect, and what does it not guarantee?
5. How do you determine whether a prune operation is destructive?
6. What must be restored before Argo CD can recover a remote cluster?
7. Why must recovery validation include the observed running image digest?
8. How would you measure RPO/RTO for a database-dependent service?

## 25. References

- [Argo CD Rollback](https://argo-cd.readthedocs.io/en/stable/user-guide/commands/argocd_app_rollback/)
- [Argo CD Automated Sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)
- [Argo CD Sync Options](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/)
- [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Kubernetes Probes](https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/)
- [Kubernetes Pod Disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [PostgreSQL Continuous Archiving and PITR](https://www.postgresql.org/docs/current/continuous-archiving.html)

---

**Chapter 054 complete.** Next: **Chapter 055 — Enterprise Environment Promotion and Release Governance Capstone**, completing Part 11.
