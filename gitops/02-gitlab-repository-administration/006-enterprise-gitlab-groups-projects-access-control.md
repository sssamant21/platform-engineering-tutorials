# Chapter 006 — Enterprise GitLab Repository Administration, Groups, Projects and Access Control

**Part 02 — GitLab Repository Administration**  
**Track:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Reference:** EKS / AKS / GKE; shared Kubernetes cluster with separate `demo-dev`, `demo-test`, `demo-staging`, `demo-prod` namespaces  
**Lab:** Disposable GitLab group and project with generic names only

## 1. Learning objectives

After this chapter, you can:

1. Design a GitLab group/subgroup/project hierarchy for application, platform, and GitOps responsibilities.
2. Explain inheritance, direct membership, role permissions, service accounts and least privilege.
3. Configure safe project visibility, branch rules, merge approval policies and CI runner boundaries.
4. Separate development, build, and production release permissions.
5. Audit membership, tokens, project settings and access changes.
6. Validate access boundaries using a practical non-production lab.
7. Troubleshoot access-denied and unintended-permission scenarios.

## 2. Enterprise architecture

```text
GitLab instance
└── platform-engineering/                  # Top-level group
    ├── applications/                      # Product teams
    │   └── demo-app/                      # Application source + CI
    ├── helm-charts/                       # Chart maintainers
    │   └── demo-app-chart/                # Versioned Helm chart
    ├── gitops/                            # Deployment desired state
    │   └── platform-environments/         # dev/test/staging/prod
    └── platform-automation/               # Privileged automation
        └── release-orchestration/         # Restricted service identity
```

**Boundary principle:** A developer who can merge application code should not automatically be able to change production GitOps configuration or Argo CD administration.

| Area | Primary owners | Allowed operations |
| --- | --- | --- |
| Application source | Application maintainers | Develop, review, merge under branch rules |
| Helm charts | Platform maintainers | Version, review and publish charts |
| GitOps Dev/Test | Application + platform teams | Reviewed environment configuration changes |
| GitOps Staging | Release/platform owners | Controlled promotion |
| GitOps Production | Restricted release/platform owners | Approved production desired-state changes |
| GitLab runners | CI platform administrators | Register, scope, secure and monitor runners |
| Argo CD control plane | Platform administrators | Manage Projects, sync policies, credentials |

GitLab project permissions, GitOps approvals, Argo CD RBAC and Kubernetes RBAC are **different enforcement layers**. All must be configured and tested.

## 3. Groups, subgroups and projects

### Group

A group organizes projects, memberships, runners, settings, access tokens and governance. Membership may be inherited by subgroups and projects.

### Subgroup

A subgroup enables delegation and separation by business capability, trust boundary or operational ownership. Do not assume a subgroup blocks access inherited from a parent group.

### Project

A project holds Git repositories, merge requests, CI/CD configuration, registries, settings, issues and access policies. Apply project-specific protections to sensitive GitOps or release repositories.

### Visibility

- **Private:** Access limited to authorized members; recommended default for internal enterprise projects.
- **Internal:** May expose projects to a broader authenticated population on eligible GitLab deployments; do not use without an explicit policy.
- **Public:** Suitable only for intentionally public content, with no confidential files or secrets.

**Governance:** Set a restrictive default visibility, prevent unauthorized visibility changes, and audit external sharing.

## 4. GitLab roles and effective permissions

Common GitLab roles include Guest, Planner (where available), Reporter, Developer, Maintainer and Owner; exact role names and capabilities depend on version, deployment and tier.

| Role | Illustrative purpose | Guidance |
| --- | --- | --- |
| Guest / Planner | Limited collaboration | Avoid granting broader source access than needed |
| Reporter | Read-only analysis, logs and reports | Review artifact and registry exposure |
| Developer | Branch development and merge requests | No direct protected production push |
| Maintainer | Project administration and approvals | Small, accountable set |
| Owner | Group-level administration | Very restricted, audited |

**Do not rely on this table as a permission matrix.** Consult the GitLab version's role-permissions reference and verify effective access. Inherited membership, shared groups, custom roles and project settings can change what an individual can do.

### Effective-access investigation

For each sensitive project, review:

1. Direct project membership.
2. Parent group and subgroup inherited membership.
3. Group/project shares and invited groups.
4. Custom roles and service accounts.
5. Personal, project and group access tokens.
6. Deploy tokens and deploy keys.
7. Protected branch/tag rules and approval requirements.
8. Runner assignments and CI/CD variable scopes.

## 5. Enterprise identity and access standard

- Use enterprise SSO/SAML or supported centralized identity integration.
- Enforce MFA and lifecycle-based access provisioning/deprovisioning.
- Map teams to GitLab groups; avoid granting permissions user by user unless justified.
- Restrict Owner and Maintainer roles.
- Use dedicated service accounts or supported project/group access tokens for automation.
- Give automation the minimum API scope and shortest practical token lifetime.
- Rotate credentials and audit inactive tokens, unused memberships and external collaborators.
- Restrict privileged runners to trusted protected refs and authorized projects.
- Enforce independent reviewers for production GitOps paths.
- Maintain break-glass access with time limits, logging and post-incident review.

### Why CI identities need special treatment

Pipeline code is executable code. A token available to an untrusted merge-request job can be stolen or abused. A protected branch alone is insufficient if untrusted pipeline configuration can be executed with privileged credentials. Verify runner isolation, protected variables, pipeline source, merge request provenance and token permissions.

## 6. Repository and release governance

### Application repository

- Protected default branch.
- Short-lived feature branches.
- Passing MR pipeline and independent review.
- CODEOWNERS for CI, container build and security-sensitive paths.
- No production deployment credentials in untrusted jobs.

### Helm repository

- Versioned charts and review of templates.
- Lint/template tests and security checks.
- Restricted chart publication permissions.
- Pinned dependencies and chart provenance where supported.

### GitOps repository

- Separate directories for environment desired state.
- Protected production paths and CODEOWNERS.
- Production image digests and chart versions pinned.
- Release approval distinct from application code approval.
- Argo CD Project restrictions and controlled production synchronization.

**Production note:** CODEOWNERS is not automatically an enforced approval rule on every GitLab tier. Verify the project actually requires the expected code-owner approval.

## 7. Hands-on lab — group/project access and permission testing

### Prerequisites

- GitLab test instance or a disposable group where you have permission to manage memberships.
- Two test identities (for example, one Developer and one Reporter) authorized for training.
- No production projects, secrets or real users should be modified.
- The lab assumes GitLab web UI; labels may vary by version.

### Step A — Create a disposable group

Create a group such as `training-platform` with **Private** visibility.

Create subgroups:

```text
training-platform/
├── applications/
├── helm-charts/
└── gitops/
```

Create projects:

```text
training-platform/applications/demo-app
training-platform/helm-charts/demo-app-chart
training-platform/gitops/platform-environments
```

If your organization prohibits top-level group creation, use an authorized disposable subgroup under an existing training group.

### Step B — Configure membership

- Grant test user A **Developer** in `applications/demo-app`.
- Grant test user B **Reporter** in `applications/demo-app`.
- Do **not** grant either test user access to `gitops/platform-environments` unless needed for a specific read-only test.
- Keep group/project Owner access limited to the lab administrator.

Inspect the **Members** page for each project and verify whether access is direct or inherited.

### Step C — Protect the default branch

In `applications/demo-app`, configure a protected `main` branch:

1. No direct pushes for ordinary Developers.
2. Merge requests required.
3. Passing pipeline required where applicable.
4. Independent reviewer required by your policy.
5. Force-push disabled.

Configure a simple validation pipeline if the project does not already have one:

```yaml
workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
    - when: never

stages: [validate]

validate:
  stage: validate
  image: alpine:3.21
  script:
    - echo "Validating training repository"
    - test -f README.md
```

Ensure an authorized runner is available before making successful pipeline execution a required merge condition.

### Step D — Test effective permissions

As **Developer A**:
- Clone the application project.
- Create a feature branch and push it.
- Open a merge request.
- Attempt a direct push to protected `main`; it should be rejected under the configured rules.
- Verify that access to the private GitOps project is denied if no inherited or shared permission exists.

As **Reporter B**:
- Verify repository read access.
- Verify that repository pushes and merges are not allowed.

As the lab administrator:
- Confirm no parent-group membership unintentionally grants broader access.
- Review protected branch rules, runner assignments, project tokens and CI variables.

**Important:** Use separate test sessions or identities to avoid accidentally testing with the administrator's cached credentials. Never test bypasses against production repositories.

### Step E — Collect evidence

Capture:

```text
[ ] Group/subgroup/project hierarchy
[ ] Private visibility settings
[ ] Direct and inherited membership inventory
[ ] Developer feature-branch push succeeds
[ ] Developer direct main push rejected
[ ] Reporter write attempt rejected
[ ] Private GitOps access denied for unauthorized user
[ ] Merge request approvals and pipeline status
[ ] Runner scope and privileged token inventory
```

An unexpected permission grant is a failed test. Investigate inherited roles, shares and custom role permissions before proceeding.

### Step F — Cleanup

Remove test users from the disposable projects and delete only the training resources you created, after verifying no shared resources depend on them. Do not delete a group or project that other teams use.

## 8. Optional read-only GitLab API inventory

For authorized projects, an administrator may inventory project membership and protected branches using the GitLab REST API. Use a token with only the scopes required by your instance, and keep it out of terminal history, CI logs and shared files.

Example endpoints (replace placeholders and authenticate through your approved secure method):

```text
GET /api/v4/projects/:id/members/all
GET /api/v4/projects/:id/protected_branches
GET /api/v4/projects/:id/access_tokens
GET /api/v4/groups/:id/members/all
```

API visibility and endpoint permissions depend on GitLab version and role. Never publish token values or full membership exports containing personal information in public tutorial repositories.

## 9. Troubleshooting runbook

| Symptom | Likely cause | Investigation |
| --- | --- | --- |
| Unexpected repository access | Inherited group membership or shared group | Review `Members` and `members/all` |
| Developer cannot push feature branch | Role, branch rule, token scope | Check effective permissions and push rules |
| Developer can push to `main` | Branch protection misconfigured | Verify allowed-to-push policy |
| CODEOWNERS not enforced | Tier, file location, approval settings | Confirm required approval rule |
| Pipeline cannot run | Runner unavailable or restricted | Inspect runner tags, scope and protection |
| Bot token can modify production | Excessive role or token scope | Revoke/rotate and reduce permissions |
| GitOps repo inaccessible to Argo CD | Repository credential or project restriction | Check repository credentials and Argo CD Project policy |
| Access persists after removal | Other inherited/share membership or active tokens | Inventory all access paths; revoke as needed |

## 10. Production acceptance checklist

- [ ] Groups and projects follow a documented ownership hierarchy.
- [ ] Sensitive projects are private by default.
- [ ] Identity lifecycle and MFA/SSO policies are enforced.
- [ ] Group inheritance and project shares are reviewed.
- [ ] Owner/Maintainer assignments are restricted and audited.
- [ ] Protected branch and tag rules are tested.
- [ ] CI runners and privileged variables are restricted to trusted jobs.
- [ ] Bot tokens have minimum scopes, expiration and rotation.
- [ ] Production GitOps permissions are separate from application development permissions.
- [ ] CODEOWNERS and required approvals are actually enforced.
- [ ] Argo CD and Kubernetes access controls are independently verified.
- [ ] Break-glass and access revocation procedures are documented and tested.

## 11. Knowledge checks

1. Why can a user retain project access after being removed from direct membership?
2. What is the difference between a GitLab group role and a protected-branch rule?
3. Why is Developer access to source code not sufficient justification for production GitOps access?
4. Why are CI/CD runner and token permissions part of repository administration?
5. Why must CODEOWNERS approval enforcement be verified?
6. What evidence proves that an access-control boundary is effective?

## 12. Completion criteria

**Pass:** You can create an authorized group/project hierarchy, verify inherited versus direct access, demonstrate successful and denied operations using distinct test identities, enforce branch protections, and document a least-privilege release governance model.

**Next: Chapter 007 — GitLab Protected Branches, Tags, CODEOWNERS and Approval Policies.**
