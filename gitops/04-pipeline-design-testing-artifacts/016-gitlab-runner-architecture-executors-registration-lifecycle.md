# Chapter 016 — GitLab Runner Architecture, Executors, Registration and Lifecycle

**Part 04 — Pipeline Design, Testing and Artifacts** | **Chapter 016 / 100**  
**Audience:** Platform engineers, SREs, DevOps engineers and GitLab administrators  
**Lab:** Disposable GitLab project and isolated Docker-based GitLab Runner  
**Cloud context:** AWS EKS, Azure AKS and Google GKE; Dev/Test/Staging/Prod are namespaces in a shared cluster, not separate clusters.

> **Safety:** Register only a runner you are authorized to manage. Use a disposable training machine or VM. Do not install a privileged runner on a production Kubernetes node, attach a host Docker socket to untrusted jobs, or place production credentials in runner configuration.

## 1. Learning objectives

After this chapter, you should be able to:

1. Explain how GitLab schedules CI jobs onto runners.
2. Compare shell, Docker, Kubernetes and other runner executors.
3. Register a runner using a modern runner authentication token workflow.
4. Configure runner tags, concurrency, protection and project/group scope.
5. Run and troubleshoot a nonprivileged Docker executor job.
6. Distinguish runner registration, token rotation, pause, retirement and cleanup.
7. Plan secure runner pools for untrusted MR validation and trusted release automation.
8. Collect operational evidence and define runner reliability indicators.

## 2. GitLab Runner architecture

```text
Developer -> GitLab repository / merge request
                       |
                       v
                GitLab CI scheduler
                       |
            Eligible pending jobs
                       |
        +--------------+--------------+
        |              |              |
        v              v              v
    MR runners    Trusted build   Release runners
    unprivileged  restricted      protected/approved
        |              |              |
   Docker executor   Docker/K8s     Kubernetes executor
        |              |              |
        +--------------+--------------+
                       |
                 Job logs/status
                       |
                       v
             GitLab pipeline results
```

GitLab coordinates pipelines and job eligibility. GitLab Runner polls for and executes eligible jobs according to configuration, runner availability, tags, protected status, capacity and executor capabilities.

**Trust boundary:** A runner executes repository-controlled code. Treat jobs from unreviewed branches and external contributors as untrusted.

## 3. Runner types and scopes

| Scope | Typical ownership | Considerations |
| --- | --- | --- |
| Instance runner | Central platform team | Broad blast radius; enforce trust boundaries |
| Group runner | Team/platform group | Inherited availability; review project access |
| Project runner | Project owner | Smaller scope; easier isolation |
| Protected runner | Trusted refs | Only eligible protected-ref jobs; verify GitLab settings |
| Dedicated release runner | Platform/release team | Restrict projects, identities, network and credentials |

Runner *scope* is not equivalent to isolation. A shared executor host can leak information through unsafe mounts, caches, privileged mode or poor tenant boundaries. Prefer separate runner infrastructure for materially different trust levels.

## 4. Executor comparison

| Executor | Isolation and operations | Recommended use |
| --- | --- | --- |
| Shell | Jobs run directly on runner host | Only highly trusted, isolated workflows |
| Docker | Jobs run in containers | General CI with unprivileged configuration |
| Kubernetes | Jobs execute in cluster pods | Scalable platform CI with hardened namespace and RBAC |
| SSH | Remote execution | Specialized legacy workflows; tightly restrict |
| Custom | Organization-defined executor | Advanced use with operational ownership |

### Docker executor

Advantages: reproducible container environment, easy lab setup, straightforward resource controls.

Risks: privileged mode, Docker socket mounting, shared host kernel, uncontrolled images and cache leakage. Container execution alone is not a strong hostile-tenant boundary.

### Kubernetes executor

Advantages: ephemeral job pods, scheduling, resource limits and namespace controls.

Risks: runner service account privilege, pod admission, network access, node placement, secrets and cluster API permissions. **Do not run untrusted CI on production workload nodes without deliberate hardening and isolation.** For critical environments, dedicated CI clusters are preferable.

### Shell executor

Shell jobs run on the host with the runner service identity. Avoid for untrusted merge requests and privileged shared hosts.

## 5. Modern runner creation and authentication

Modern GitLab versions use a runner-creation workflow in the GitLab UI/API, which provides a runner authentication token, commonly beginning with `glrt-`. Legacy registration tokens and some old `gitlab-runner register` flags have been deprecated or restricted.

**Use the workflow supported by your GitLab version.** Create the runner in the authorized GitLab UI, set its description, tags, project/group scope and protection policy, and copy the authentication token securely. Never commit it or paste it into chat, screenshots or job logs.

Typical Linux registration:

```bash
sudo gitlab-runner register \
  --non-interactive \
  --url "https://gitlab.example.com" \
  --token "$GITLAB_RUNNER_TOKEN" \
  --executor "docker" \
  --docker-image "python:3.12-slim" \
  --description "training-docker-runner"
```

Here `GITLAB_RUNNER_TOKEN` is supplied securely in the operator's local shell, not stored in repository files. Avoid passing real token values in shell history. The GitLab UI manages runner metadata in the modern workflow; not all legacy registration options apply to runner authentication tokens.

### Inspect configuration

Typical location on a Linux service install: `/etc/gitlab-runner/config.toml`.

```toml
concurrent = 2
check_interval = 0

[[runners]]
  name = "training-docker-runner"
  url = "https://gitlab.example.com"
  executor = "docker"
  limit = 2
  [runners.docker]
    image = "python:3.12-slim"
    privileged = false
    volumes = ["/cache"]
```

This is an **illustrative sanitized excerpt**. A real configuration includes runner identity and token fields; never copy them into documentation. Preserve generated fields when editing the real file. Some runner settings may be managed centrally in GitLab rather than via `config.toml`.

## 6. Hands-on lab — isolated Docker runner

### Prerequisites

- An authorized disposable GitLab project: `https://gitlab.example.com/training/demo-app`.
- Linux VM with Docker Engine and GitLab Runner installed, or a similarly isolated training host.
- Outbound HTTPS access to GitLab and a container registry.
- Runner operator access to the GitLab project.
- A nonprivileged runner with no host Docker socket passed to jobs.

**Install GitLab Runner using the vendor's supported package/repository procedure for your Linux distribution and version.** Verify the installed binary before proceeding:

```bash
gitlab-runner --version
docker version
```

Do not assume installation commands for one distribution apply to another.

### Step 1 — Create runner in GitLab

In the project, navigate to **Settings → CI/CD → Runners** (UI labels vary). Create a project runner with:

- Description: `training-docker-runner`
- Tag: `training-docker`
- Run untagged jobs: **disabled**
- Protected: **disabled** for this disposable MR lab
- Lock to current project / restrict scope as supported
- No privileged credentials

Record runner ID and configuration, **not** its authentication token.

### Step 2 — Register on the isolated host

Set `GITLAB_RUNNER_TOKEN` through a secure local mechanism, then register using the command in Section 5. For example, in an interactive shell with history disabled for the session:

```bash
read -r -s -p "Runner authentication token: " GITLAB_RUNNER_TOKEN
printf '\n'
export GITLAB_RUNNER_TOKEN
sudo --preserve-env=GITLAB_RUNNER_TOKEN gitlab-runner register \
  --non-interactive \
  --url "https://gitlab.example.com" \
  --token "$GITLAB_RUNNER_TOKEN" \
  --executor "docker" \
  --docker-image "python:3.12-slim" \
  --description "training-docker-runner"
unset GITLAB_RUNNER_TOKEN
```

**Operator note:** The command-line token argument can be visible briefly to local process inspection. For high-security environments use the supported runner setup procedure and secret-handling controls for your installation method. Never place tokens in source control. The `sudo --preserve-env` behavior depends on local sudo policy; if blocked, use a supported protected environment-file or service deployment mechanism rather than weakening policy.

### Step 3 — Check runner health

```bash
sudo gitlab-runner verify
sudo gitlab-runner status
sudo systemctl status gitlab-runner --no-pager
```

Commands depend on installation type; `systemctl` applies to service-managed Linux installations. `verify` checks registration connectivity, not full executor functionality.

### Step 4 — Create sample repository

```text
demo-app/
├── .gitlab-ci.yml
├── README.md
└── tests/
    └── test_smoke.py
```

`tests/test_smoke.py`:

```python
import unittest


class SmokeTests(unittest.TestCase):
    def test_runner(self):
        self.assertEqual(2 + 2, 4)


if __name__ == "__main__":
    unittest.main()
```

`README.md`:

```markdown
# demo-app

Disposable GitLab Runner architecture and lifecycle lab.
```

`.gitlab-ci.yml`:

```yaml
workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
    - when: never

stages:
  - validate
  - test

default:
  image: python:3.12-slim
  tags:
    - training-docker

runner_environment:
  stage: validate
  script:
    - python --version
    - python -c 'import os; assert os.environ.get("CI_RUNNER_ID"); print("PASS: runner assigned")'

smoke_tests:
  stage: test
  needs:
    - runner_environment
  script:
    - python -m unittest discover -s tests -v
```

Expected: both jobs run on the eligible training runner.

### Step 5 — Push and open an MR

```bash
git clone https://gitlab.example.com/training/demo-app.git
cd demo-app
git switch main
git pull --ff-only origin main
git switch -c feature/ch016-runner-lab
# Add the sample files above
git add .gitlab-ci.yml README.md tests/
git commit -m "ci: validate isolated training runner"
git push -u origin feature/ch016-runner-lab
```

Create an MR. Validate YAML with GitLab CI Lint. Confirm job details show the expected runner ID, tag and executor.

### Step 6 — Negative test: unmatched tag

Temporarily change the job tag to:

```yaml
tags:
  - training-runner-tag-not-configured
```

Expected: job remains pending because no runner matches. Capture job status and runner eligibility information. Restore `training-docker`, push and confirm recovery.

Do not disable shared runners to create this failure.

### Step 7 — Negative test: runner pause

Pause **only the disposable runner** in the GitLab UI. Trigger a new MR pipeline and observe pending jobs. Resume the runner and confirm processing recovers. Do not pause any production or shared runner.

### Step 8 — Concurrency observation

Create multiple disposable pipelines or add harmless independent test jobs. Record pending time and execution overlap. Compare observed concurrency with global `concurrent`, runner `limit`, executor constraints and GitLab runner settings.

Do not overload the host; keep CPU and memory use bounded.

### Step 9 — Retirement and cleanup

After completing the lab:

1. Pause the disposable runner.
2. Ensure no jobs are running.
3. Remove/delete the runner using the GitLab UI/API supported by your version.
4. Remove the local runner configuration through supported administrative commands, only for this disposable runner.
5. Revoke/rotate the runner authentication token if exposure is suspected.
6. Remove the disposable VM/container and associated caches securely.

**Do not assume `gitlab-runner unregister` always deletes the server-side runner object**, especially when using the modern runner-creation workflow. Verify removal in GitLab.

## 7. Production runner-pool design

| Pool | Trust | Executor | Credential policy |
| --- | --- | --- | --- |
| `mr-validation` | Untrusted | Unprivileged Docker/Kubernetes | No cloud release credentials |
| `main-build` | Trusted protected refs | Isolated Docker/Kubernetes | Short-lived build/registry identity |
| `release-automation` | Restricted | Dedicated runner | Approved OIDC identity and minimal scope |

Use separate projects/groups and infrastructure when appropriate. Protected runners are useful but do not replace correct ref rules, project access controls, token scope and workload isolation.

### EKS / AKS / GKE considerations

- **EKS:** Kubernetes runner pods may use IRSA or EKS Pod Identity for narrowly scoped AWS access, with dedicated service accounts and node pools.
- **AKS:** Prefer Microsoft Entra Workload ID with scoped service accounts and appropriate node isolation.
- **GKE:** Prefer Workload Identity Federation for GKE with scoped Kubernetes service accounts and IAM permissions.

These are architecture patterns, not turnkey instructions. Each requires cloud-side trust and permission configuration. Avoid giving untrusted MR runners identities capable of modifying production workloads.

### Shared cluster risk

Because Dev, Test, Staging and Prod namespaces coexist in one cluster, CI job pods must not have broad cluster RBAC or unrestricted network access to production services. Consider a dedicated CI namespace and node pool, resource quotas, network policies, admission controls and, for high-assurance workloads, a separate CI cluster.

## 8. Runner observability and capacity

Track:

| Metric | Why it matters |
| --- | --- |
| Pending job age (p95/p99) | Detect insufficient runner capacity |
| Job start latency | Detect scheduling and polling issues |
| Runner online/offline state | Detect service outages |
| Job failure by cause | Separate application failures from infrastructure failures |
| Concurrent job utilization | Right-size fleet |
| Executor startup failures | Diagnose Docker/Kubernetes/image problems |
| CPU/memory/disk/cache usage | Prevent resource exhaustion |
| Authentication failures | Detect token rotation or connectivity issues |

Runner metrics availability and endpoint configuration depend on deployment mode and version. Use supported Prometheus/Grafana integration and protect metrics endpoints from public exposure.

## 9. Troubleshooting runbook

| Symptom | Likely cause | Investigation |
| --- | --- | --- |
| Runner offline | Service stopped, TLS/network issue, invalid token | Check service, logs, connectivity and registration |
| Job stuck pending | Tag mismatch, protection, scope, concurrency | Inspect job tags and runner eligibility |
| Docker job fails before script | Image pull, Docker daemon, storage | Inspect executor logs and registry access |
| Kubernetes job pending | Quota, scheduling, RBAC, admission, image pull | Inspect pod events and runner SA permissions |
| Authentication errors | Expired/rotated/revoked runner token | Recreate/rotate using supported workflow |
| Runner overloaded | Excess concurrency or undersized host | Tune limits, scale capacity and monitor |
| Untrusted job sees secret | Incorrect runner/variable trust boundary | Revoke credentials, quarantine runner, investigate |
| Runner deletion incomplete | Local config and GitLab server object differ | Verify both sides separately |
| Runner picks unintended project | Group/instance scope too broad | Restrict availability and project permissions |

### Incident response

1. Identify runner ID, host, executor, affected projects and job window.
2. If compromise suspected, pause/quarantine the runner and revoke affected credentials.
3. Preserve authorized nonsecret evidence and relevant audit records.
4. Restore capacity using a clean runner and supported authentication workflow.
5. Validate with a disposable pipeline before re-enabling trusted jobs.
6. Document root cause, blast radius and preventive controls.

## 10. Acceptance checklist

- [ ] Runner scope, tags, protection and executor documented.
- [ ] Modern registration workflow used for deployed GitLab version.
- [ ] Runner authentication token handled securely and never committed.
- [ ] Docker executor runs with `privileged = false`.
- [ ] MR lab pipeline succeeds on intended runner.
- [ ] Unmatched-tag negative test causes pending job and recovers.
- [ ] Disposable-runner pause/resume verified.
- [ ] Runner capacity and pending-time observations recorded.
- [ ] Runner lifecycle retirement steps validated.
- [ ] Production identities unavailable to untrusted MR jobs.
- [ ] EKS/AKS/GKE workload identity and isolation patterns understood.
- [ ] No production Kubernetes cluster changes performed.

## 11. Evidence template

```text
CHAPTER 016 — RUNNER LIFECYCLE LAB
GitLab version/tier:
Training project:
Runner ID:
Runner scope:
Executor:
Runner tags:
Protected setting:
Privileged mode:
MR URL:
Pipeline ID:
Successful jobs:
Unmatched-tag negative test:
Pause/resume test:
Observed pending time:
Observed concurrency:
Runner retirement verified:
Reviewer:
Risks and follow-up:
```

## 12. Knowledge checks

1. What is the difference between runner scope and executor isolation?
2. Why are shell runners risky for untrusted MRs?
3. Why does `gitlab-runner verify` not prove a job will execute successfully?
4. Why should protected release runners be separate from MR runners?
5. What are the risks of mounting the Docker socket into CI jobs?
6. How do cloud workload identities differ across EKS, AKS and GKE?
7. Why must local runner cleanup and GitLab-side deletion both be verified?

## 13. Completion criteria

**Pass:** You register an authorized disposable runner, execute a real MR pipeline, diagnose and recover from tag mismatch and runner pause, document security boundaries and retire the runner cleanly.

**Next: Chapter 017 — GitLab Runner Security, Isolation, Autoscaling and Kubernetes Executors.**
