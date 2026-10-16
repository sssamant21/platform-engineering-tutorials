# Chapter 012 — Jenkins Agent Architecture, Launch Methods and Secure Connectivity

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 03:** Controller, Agents and Executors  
**Chapter:** 012 / 100  
**Companion lab:** [012 — Jenkins Agent Launch and Connectivity Check](labs/012-jenkins-agent-launch-connectivity-check.md)

> **Safety:** Use a disposable localhost Jenkins controller. Never disable TLS verification or SSH host-key verification to make an agent connect. Never grant an untrusted agent controller admin credentials or mount the host Docker socket.

## 1. Learning objectives

Compare static and ephemeral Jenkins agents; configure secure SSH, inbound TCP and WebSocket launch methods; understand Java remoting, node labels, executor sizing and workspaces; design Kubernetes/VM agent provisioning; troubleshoot agent connectivity and resource incidents.

## 2. Architecture

```text
SCM / users -> trusted HTTPS proxy -> Jenkins controller (0 executors)
                                        |
                              queue + label scheduler
                                        |
          +-----------------------------+---------------------------+
          |                             |                           |
   SSH static agent               Inbound agent             Ephemeral agent
   controller -> host             agent -> controller       Kubernetes / cloud VM
   host-key + SSH auth            TCP or WebSocket          identity + pod/VM policy
          |                             |                           |
    isolated workspace             isolated workspace       disposable workspace
          +-----------------------------+---------------------------+
                                        |
                              build/test/scan -> registry
```

The controller coordinates builds and stores durable metadata. Agents execute workspace-dependent steps. Jenkins remoting is not a substitute for host/network isolation.

## 3. Launch method comparison

| Method | How it works | Required security controls |
|---|---|---|
| SSH-launched static agent | Controller opens SSH to trusted host; manages Java remoting process | Restricted SSH key, host-key verification, non-root account, supported Java |
| Inbound agent (TCP) | Agent initiates connection to controller inbound listener | Agent-specific secret, authenticated encrypted transport, restricted listener |
| Inbound agent (WebSocket) | Agent initiates HTTP(S) upgrade via reverse proxy | TLS, proxy WebSocket headers, token protection, timeouts |
| Kubernetes ephemeral agent | Plugin provisions per-build pod and remoting container | Kubernetes RBAC, pod security, workload identity, cleanup |
| Cloud VM ephemeral agent | Cloud plugin creates/destroys compute per demand | Least-privilege cloud identity, immutable images, tagging, TTL |

## 4. Agent identity, Java and filesystem requirements

- Each agent needs a unique node name, authorized launch identity, working Java runtime and dedicated writable remote root.
- Jenkins core, agent remoting and Java versions must be compatible; confirm with the version-specific Jenkins requirements and plugin release notes.
- Use a non-root service account and filesystem ACLs limiting cross-job access.
- Keep agent credentials short-lived or rotateable, never embed them in Jenkinsfile, shell history or screenshots.
- Prefer one executor for resource-intensive or untrusted workloads unless measured evidence supports more.
- Keep trusted deployment agents separate from untrusted PR build agents.

## 5. Disposable controller for the lab

```bash
docker version
docker volume create jenkins-ch012-home
docker run -d --name jenkins-ch012 --restart=no \
  -p 127.0.0.1:8090:8080 \
  --memory 4g --cpus 2 \
  --mount source=jenkins-ch012-home,target=/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
docker ps --filter name=jenkins-ch012
docker logs --tail 80 jenkins-ch012
docker port jenkins-ch012
```

The mutable image tag is for a disposable lab; pin an approved digest for production. Unlock privately at `http://127.0.0.1:8090`, create a named admin and set built-in executors to zero.

## 6. Secure SSH static agent setup (approved staging only)

On a separate trusted Linux agent host:

```bash
sudo useradd --system --create-home --shell /bin/bash jenkins-agent
sudo install -d -o jenkins-agent -g jenkins-agent -m 0700 /home/jenkins-agent/.ssh
sudo install -d -o jenkins-agent -g jenkins-agent -m 0750 /home/jenkins-agent/workspace
java -version
```

Provision the **public** half of a dedicated SSH key into `authorized_keys` with restricted ownership and mode. Keep the private key in Jenkins credentials. Verify the SSH server's host key fingerprint out-of-band and configure strict host-key verification. In Jenkins, install an approved SSH Build Agents plugin, create a permanent node, set remote root and labels, select SSH launch and the dedicated credentials.

Do not use a shared personal SSH account or `StrictHostKeyChecking=no`.

## 7. Inbound TCP and WebSocket agent design

Inbound agents initiate the connection. The exact launch command and secret are generated per node by Jenkins and may change by core/remoting version. Retrieve the supported command privately from the node page; do not copy secrets into the tutorial.

For WebSocket, the controller's canonical HTTPS URL and proxy WebSocket upgrade headers must work. For inbound TCP, restrict the agent listener and require authenticated, encrypted transport. Prefer WebSocket when approved network design avoids opening an extra inbound port.

## 8. Kubernetes ephemeral agent architecture

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: jenkins-agent-example
  labels:
    app: jenkins-agent
spec:
  restartPolicy: Never
  serviceAccountName: jenkins-agent
  securityContext:
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: jnlp
      image: jenkins/inbound-agent:latest-jdk21
      resources:
        requests:
          cpu: 250m
          memory: 512Mi
        limits:
          cpu: "1"
          memory: 1Gi
```

This is an **architecture illustration**, not a standalone functional Jenkins agent: the Jenkins Kubernetes plugin normally injects connection configuration and manages pod lifecycle. Production must pin the image digest, review pod identity, disable unnecessary service-account token mounting and enforce namespace/network policy. Avoid privileged builds and Docker socket mounts.

## 9. Labels, executors and queue behavior

```groovy
pipeline {
  agent none
  stages {
    stage('Build') {
      agent { label 'trusted-linux-build' }
      steps {
        sh 'id && hostname && pwd'
      }
    }
  }
}
```

This Pipeline deliberately requires a pre-provisioned agent with the label. If none exists, the job queues. Use agent labels to express workload capabilities, not as a security control by themselves.

## 10. Observability and capacity planning

Track online/offline state, connection errors, remoting disconnects, queue wait, executor utilization, workspace disk/inodes, JVM/CPU/memory, provisioning latency, pod evictions and orphaned cloud resources. Define fleet ownership, SLOs and alert escalation.

## 11. Twenty agent failure scenarios

| # | Symptom | Investigation | Safe remediation |
|---|---|---|---|
| 1 | SSH connection refused | Host port/firewall and daemon | Restore restricted SSH connectivity |
| 2 | SSH host-key verification fails | Known_hosts, host fingerprint and rotation | Verify identity and update approved trust |
| 3 | SSH authentication denied | Agent account, key permissions and credential scope | Repair least-privilege SSH identity |
| 4 | Remote Java missing | java -version on agent host | Install supported runtime |
| 5 | Agent.jar/remoting incompatibility | Controller/agent Java and remoting logs | Use compatible Java/remoting |
| 6 | Inbound agent secret invalid | Node identity and credential rotation | Rotate only affected secret |
| 7 | Inbound TCP port blocked | Listener configuration, firewall and DNS | Use approved secure route or WebSocket |
| 8 | WebSocket upgrade 400/502 | Proxy Upgrade/Connection and upstream | Repair trusted proxy |
| 9 | TLS trust failure | CA bundle, SAN, hostname, clock | Install trusted CA and valid certificate |
| 10 | Agent keeps disconnecting | Remoting logs, OOM, network idle timeouts | Repair connectivity/resources |
| 11 | Agent offline but host healthy | Node state and launch logs | Reconnect after root cause |
| 12 | Job stuck waiting for label | Label expression and online agents | Provision matching capacity |
| 13 | All executors busy | Executor utilization and queue time | Scale isolated agents or reduce contention |
| 14 | Workspace permissions denied | Agent UID/GID, volume ACL | Correct non-root workspace permissions |
| 15 | Workspace disk full | Agent df -h/df -i and retention | Expand or approved cleanup |
| 16 | Kubernetes pod Pending | kubectl describe, quotas, scheduling | Fix requests/taints/capacity |
| 17 | Kubernetes pod ImagePullBackOff | Pod events and registry auth | Repair approved image/credentials |
| 18 | Cloud agent provision fails | IAM, quotas, API logs and template | Correct least-privilege provisioning |
| 19 | Agent exposed to untrusted secrets | Job/credential scope and SCM trust | Quarantine and rotate credentials |
| 20 | Orphaned ephemeral agents | Cloud/pod lifecycle and TTL | Reconcile and clean with ownership checks |

## 12. Eight SRE runbooks

### RB-01 SSH launch failure

**Procedure:** Check agent host identity, SSH port, key, known_hosts, Java, permissions and controller launch logs.

**Exit criteria:** authenticated agent transport, matching label/executor capacity, least-privilege runtime, stable workspace, job smoke and recorded incident evidence.

### RB-02 Inbound/WebSocket connection outage

**Procedure:** Validate TLS, agent secret, proxy upgrade, remoting versions and restricted listener.

**Exit criteria:** authenticated agent transport, matching label/executor capacity, least-privilege runtime, stable workspace, job smoke and recorded incident evidence.

### RB-03 Agent capacity starvation

**Procedure:** Correlate queue reasons, labels, executors, cloud quotas and provisioning latency.

**Exit criteria:** authenticated agent transport, matching label/executor capacity, least-privilege runtime, stable workspace, job smoke and recorded incident evidence.

### RB-04 Kubernetes pod agent failure

**Procedure:** Inspect namespace, service account, pod events, scheduling, image pull and workspace volumes.

**Exit criteria:** authenticated agent transport, matching label/executor capacity, least-privilege runtime, stable workspace, job smoke and recorded incident evidence.

### RB-05 Credential exposure on agent

**Procedure:** Quarantine agent/job, revoke and rotate, audit logs, rebuild ephemeral image and permissions.

**Exit criteria:** authenticated agent transport, matching label/executor capacity, least-privilege runtime, stable workspace, job smoke and recorded incident evidence.

### RB-06 Agent resource pressure

**Procedure:** Inspect CPU, memory, OOM, disk/inodes, workspace cleanup and noisy neighbors.

**Exit criteria:** authenticated agent transport, matching label/executor capacity, least-privilege runtime, stable workspace, job smoke and recorded incident evidence.

### RB-07 Agent version compatibility

**Procedure:** Compare controller LTS, remoting, Java and plugins; test upgrades in staging.

**Exit criteria:** authenticated agent transport, matching label/executor capacity, least-privilege runtime, stable workspace, job smoke and recorded incident evidence.

### RB-08 Agent fleet operational handoff

**Procedure:** Record identity, transport, labels, images, owner, alerts, cleanup and rollback.

**Exit criteria:** authenticated agent transport, matching label/executor capacity, least-privilege runtime, stable workspace, job smoke and recorded incident evidence.

## 13. Acceptance gates

| Gate | Required evidence |
|---|---|
| G1 | Controller built-in executors zero |
| G2 | Static vs ephemeral launch methods compared |
| G3 | SSH host-key verification and dedicated identity designed |
| G4 | Inbound TCP/WebSocket trust boundary documented |
| G5 | Compatible Java/remoting versions reviewed |
| G6 | Node labels and executor scheduling explained |
| G7 | Kubernetes/cloud ephemeral security reviewed |
| G8 | Agent telemetry and alerts specified |
| G9 | Three agent incidents and rollback rehearsed |
| G10 | No secret exposure, safe cleanup and evidence complete |

## 14. Assessment — 100 points

| Domain | Points |
|---|---:|
| Agent architecture and launch methods | 20 |
| SSH, inbound and WebSocket security | 25 |
| Java, labels and executor scheduling | 20 |
| Kubernetes/cloud agents | 15 |
| Troubleshooting and monitoring | 10 |
| Cleanup and evidence | 10 |
| **Total** | **100** |

**Pass:** 90+ with all mandatory security gates. Local design exercises do not certify a live production agent connection.

## 15. Safe cleanup

```bash
docker stop jenkins-ch012
docker rm jenkins-ch012
# Destructive only after verifying this is an exclusively lab-owned volume:
docker volume rm jenkins-ch012-home
```

**Next:** Chapter 013 — Jenkins Nodes, Labels, Executors and Workload Scheduling.
