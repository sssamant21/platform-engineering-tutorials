# Chapter 009 — Hands-On Lab: Jenkins Reverse Proxy, HTTPS and Networking Check

**Parent:** [Chapter 009](../009-jenkins-reverse-proxy-https-networking-access-configuration.md)

## Scope and safety

The executable lab tests a disposable loopback-bound controller; production TLS/SSO/webhook tests are **design/tabletop tasks** unless an approved staging hostname, certificate and proxy are available. Never expose port 8087 publicly or turn off security.

## Lab 01 — Inspect Docker and port availability

```bash
docker version
docker ps
```

**Follow-up:** Capture redacted output and document the security/operational finding.

**Pass:** Docker ready and port free. **Rollback:** revert only approved staging changes or remove the disposable lab.

## Lab 02 — Create dedicated volume

```bash
docker volume create jenkins-ch009-home
docker volume inspect jenkins-ch009-home
```

**Follow-up:** Capture redacted output and document the security/operational finding.

**Pass:** Dedicated volume exists. **Rollback:** revert only approved staging changes or remove the disposable lab.

## Lab 03 — Start loopback Jenkins

```bash
docker run -d --name jenkins-ch009 --restart=no -p 127.0.0.1:8087:8080 --mount source=jenkins-ch009-home,target=/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Follow-up:** Capture redacted output and document the security/operational finding.

**Pass:** Controller starts privately. **Rollback:** revert only approved staging changes or remove the disposable lab.

## Lab 04 — Review startup logs

```bash
docker logs --tail 80 jenkins-ch009
```

**Follow-up:** Capture redacted output and document the security/operational finding.

**Pass:** No fatal startup errors. **Rollback:** revert only approved staging changes or remove the disposable lab.

## Lab 05 — Inspect published port

```bash
docker port jenkins-ch009
```

**Follow-up:** Capture redacted output and document the security/operational finding.

**Pass:** Bound only to 127.0.0.1:8087. **Rollback:** revert only approved staging changes or remove the disposable lab.

## Lab 06 — Check local HTTP response

```bash
curl --silent --show-error --head http://127.0.0.1:8087/login
```

**Follow-up:** Capture redacted output and document the security/operational finding.

**Pass:** Expected login response or redirect. **Rollback:** revert only approved staging changes or remove the disposable lab.

## Lab 07 — Complete private bootstrap

```bash
docker exec jenkins-ch009 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Follow-up:** Complete bootstrap privately at http://127.0.0.1:8087; never save the unlock password in evidence.

**Pass:** Named lab admin created; token private. **Rollback:** revert only approved staging changes or remove the disposable lab.

## Lab 08 — Set controller executors zero

```bash
docker ps --filter name=jenkins-ch009
```

**Follow-up:** Manage Jenkins → Nodes → Built-In Node → Configure → set executors to zero.

**Pass:** Built-in node executors zero. **Rollback:** revert only approved staging changes or remove the disposable lab.

## Lab 09 — Inspect network attachment

```bash
docker inspect jenkins-ch009 --format '{{json .NetworkSettings.Networks}}'
```

**Follow-up:** Capture redacted output and document the security/operational finding.

**Pass:** Network trust boundary documented. **Rollback:** revert only approved staging changes or remove the disposable lab.

## Lab 10 — Inspect Jenkins URL settings

```bash
docker logs --tail 40 jenkins-ch009
```

**Follow-up:** Capture redacted output and document the security/operational finding.

**Pass:** Local root URL documented; production HTTPS plan. **Rollback:** revert only approved staging changes or remove the disposable lab.

## Lab 11 — Review NGINX proxy template

```bash
nginx -v 2>&1 || true
```

**Follow-up:** Review the parent chapter NGINX template; if NGINX is available on an approved staging host, validate with nginx -t after substituting real certificates.

**Pass:** NGINX design validated conceptually or on staging. **Rollback:** revert only approved staging changes or remove the disposable lab.

## Lab 12 — Review forwarded-header trust

```bash
docker port jenkins-ch009
```

**Follow-up:** Capture redacted output and document the security/operational finding.

**Pass:** Client-supplied headers not blindly trusted. **Rollback:** revert only approved staging changes or remove the disposable lab.

## Lab 13 — Design TLS certificate validation

```bash
openssl version
```

**Follow-up:** Capture redacted output and document the security/operational finding.

**Pass:** Certificate chain/renewal checklist documented. **Rollback:** revert only approved staging changes or remove the disposable lab.

## Lab 14 — Design SSO callback test

```bash
docker inspect jenkins-ch009 --format '{{.State.Status}}'
```

**Follow-up:** Capture redacted output and document the security/operational finding.

**Pass:** Canonical URL and IdP redirect mapping. **Rollback:** revert only approved staging changes or remove the disposable lab.

## Lab 15 — Design signed webhook test

```bash
docker logs --tail 40 jenkins-ch009
```

**Follow-up:** Capture redacted output and document the security/operational finding.

**Pass:** Webhook signature and delivery validation plan. **Rollback:** revert only approved staging changes or remove the disposable lab.

## Lab 16 — Review WebSocket agent transport

```bash
docker inspect jenkins-ch009 --format '{{.Config.Image}}'
```

**Follow-up:** Capture redacted output and document the security/operational finding.

**Pass:** Agent transport and proxy upgrade plan. **Rollback:** revert only approved staging changes or remove the disposable lab.

## Lab 17 — Assess firewall exposure

```bash
docker port jenkins-ch009
```

**Follow-up:** Capture redacted output and document the security/operational finding.

**Pass:** No public backend exposure. **Rollback:** revert only approved staging changes or remove the disposable lab.

## Lab 18 — Troubleshooting tabletop

```bash
docker logs --tail 100 jenkins-ch009
```

**Follow-up:** Use 502 upstream, redirect loop and webhook 403 as tabletop scenarios; do not intentionally disrupt a real endpoint.

**Pass:** Three incidents diagnosed with rollback. **Rollback:** revert only approved staging changes or remove the disposable lab.

## Lab 19 — Define monitoring and SRE handoff

```bash
docker ps --filter name=jenkins-ch009
```

**Follow-up:** Capture redacted output and document the security/operational finding.

**Pass:** TLS expiry, 5xx, latency, webhook and agent alerts. **Rollback:** revert only approved staging changes or remove the disposable lab.

## Lab 20 — Cleanup and final scoring

```bash
docker stop jenkins-ch009
docker rm jenkins-ch009
# After verifying exclusive ownership: docker volume rm jenkins-ch009-home
```

**Follow-up:** Delete only this lab-owned volume after verifying no other consumers.

**Pass:** Lab removed and assessment recorded. **Rollback:** revert only approved staging changes or remove the disposable lab.

## Optional TLS and reverse proxy validation (approved staging only)

```bash
# Replace hostname with your actual approved staging endpoint.
openssl s_client -connect jenkins.example.internal:443 \
  -servername jenkins.example.internal -showcerts </dev/null
curl --head https://jenkins.example.internal/login
```

Do not claim this test passed without a real trusted endpoint. Verify certificate SAN/chain, canonical redirects and authenticated login.

## Failure triage checklist

| Symptom | Evidence | Recovery |
|---|---|---|
| 502 | Proxy and controller logs | Restore upstream |
| Redirect loop | X-Forwarded-Proto and root URL | Correct trusted proxy headers |
| TLS error | openssl chain and expiry | Renew valid certificate |
| SSO callback failure | Redirect URI and Jenkins URL | Align trusted HTTPS URL |
| Webhook 403 | Provider delivery and signature | Repair endpoint/secret |
| Agent WebSocket fails | Upgrade headers and timeout | Configure proxy transport |
| Public backend | docker port and firewall | Restrict listener |
| Slow ingress | Proxy latency, JVM/GC | Fix backend or capacity |

## Acceptance score (100 points)

| Area | Points |
|---|---:|
| Private backend and trust model | 20 |
| TLS/reverse proxy design | 20 |
| Root URL, SSO and access | 15 |
| Webhook and agent networking | 15 |
| Troubleshooting/monitoring | 20 |
| Cleanup/evidence | 10 |
| **Total** | **100** |

**Pass:** 90+ with mandatory security gates.

## Evidence template

```text
Operator/date:
Docker/Jenkins version:
Port binding:
Root URL:
Proxy topology:
TLS chain and renewal design:
Trusted forwarding headers:
SSO callback plan:
Webhook signature verification:
Agent transport:
Three incident scenarios:
Metrics and alerts:
Cleanup proof:
Score/assessor:
```

**Next:** Chapter 010 — Jenkins Installation, Configuration and Administration Production Readiness Capstone.
