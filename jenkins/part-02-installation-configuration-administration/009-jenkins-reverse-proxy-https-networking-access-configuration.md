# Chapter 009 — Jenkins Reverse Proxy, HTTPS, Networking and Access Configuration

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 02:** Installation, Configuration and Administration  
**Chapter:** 009 / 100  
**Companion lab:** [009 — Jenkins Reverse Proxy, HTTPS and Networking Check](labs/009-jenkins-reverse-proxy-https-networking-check.md)

> **Safety:** The executable lab uses loopback HTTP only. Production Jenkins must use trusted HTTPS, authentication, restricted backend networking and approved reverse-proxy configuration. Do not expose a raw Jenkins port to the Internet or trust forwarded headers supplied by arbitrary clients.

## 1. Learning objectives

Design secure ingress to Jenkins, configure a canonical HTTPS root URL, understand reverse proxy and forwarded headers, validate TLS and SSO callbacks, secure webhooks and agent transport, troubleshoot networking, and establish operational acceptance and rollback.

## 2. Reference architecture

```text
Admin / SCM webhook / agent
              |
       DNS + trusted TLS
              |
       Reverse proxy / WAF
       - HTTPS 443
       - trusted forwarding
       - access logs / limits
              |
      private upstream network
              |
      Jenkins controller :8080
       (zero build executors)
          |           |
        SSO/RBAC    plugins
          |           |
         isolated agents
```

Terminate TLS at an approved proxy and restrict direct backend access. When TLS terminates upstream, Jenkins must be configured with the **externally visible HTTPS URL** and receive correctly sanitized forwarded headers. Backend transport may also require TLS based on organizational network policy.

## 3. Network and access components

| Component | Enterprise requirement |
|---|---|
| DNS | Stable hostname, controlled TTL, approved ownership |
| TLS | Valid certificate, modern protocols/ciphers, automated renewal |
| Reverse proxy | Trusted headers, WebSocket support where needed, bounded timeouts |
| Jenkins root URL | Canonical externally accessible HTTPS address |
| Authentication | SSO/MFA where available, named identities and audited break-glass |
| Authorization | Least privilege, folder/job permissions and protected admin access |
| Webhooks | Provider signatures/secrets, narrow endpoints, audit and replay defense |
| Agent transport | Secure authenticated connections, prefer approved modern transport |
| Firewall | Backend accessible only to trusted proxy/agents as required |
| Logging | Access logs, status codes, upstream timings, secret redaction |

## 4. Disposable localhost Jenkins backend

```bash
docker volume create jenkins-ch009-home
docker run -d --name jenkins-ch009 --restart=no \
  -p 127.0.0.1:8087:8080 \
  --mount source=jenkins-ch009-home,target=/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
docker ps --filter name=jenkins-ch009
docker port jenkins-ch009
docker logs --tail 80 jenkins-ch009
curl --silent --show-error --head http://127.0.0.1:8087/login
```

The mutable LTS tag is acceptable only for the disposable lab; pin a verified image digest for production. Complete first-run setup privately, create a named administrator, and set controller executors to zero.

## 5. Example NGINX reverse proxy (production design template)

This is a **review template**, not a deploy-ready certificate or SSO configuration. Replace names, certificates, network restrictions and upstream addresses with approved values. Configure the NGINX `map` directive inside the `http` context.

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    listen 443 ssl;
    server_name jenkins.example.internal;

    ssl_certificate     /etc/nginx/tls/fullchain.pem;
    ssl_certificate_key /etc/nginx/tls/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Port 443;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_read_timeout 90s;
        proxy_send_timeout 90s;
    }
}
```

**Trust boundary:** the proxy must be the only accepted ingress to the backend. Use an appropriate trusted-proxy configuration if behind another load balancer; do not accept arbitrary client-provided `X-Forwarded-*` values. Add organizational TLS, HSTS, logging, request size and access policies after testing.

## 6. Jenkins canonical URL and redirects

In **Manage Jenkins → System → Jenkins Location**, set the external URL, for example `https://jenkins.example.internal/`. Validate redirects and absolute links after proxy configuration.

```bash
curl -I https://jenkins.example.internal/login
curl -I http://127.0.0.1:8080/login
```

The public URL is illustrative and not expected to resolve in the local lab. Test only your actual approved hostname.

## 7. TLS certificate verification

```bash
openssl s_client -connect jenkins.example.internal:443 \
  -servername jenkins.example.internal -showcerts </dev/null
```

Inspect certificate subject/SAN, chain, expiry, trust and negotiated TLS. Never use `curl -k` to declare a production endpoint healthy.

## 8. Webhook security and SCM integrations

- Verify GitHub/GitLab webhook signature or secret according to the specific Jenkins integration.
- Use the documented plugin endpoint and narrow webhook permissions.
- Keep TLS valid, restrict provider traffic where practical and log delivery failures.
- Avoid assuming all webhook endpoints require Jenkins CSRF crumbs; behavior is plugin-specific.
- Protect untrusted pull requests from production credentials and deployment permissions.
- Test duplicate/replayed events and idempotency of triggered Pipelines.

## 9. Jenkins agent networking

Agent connectivity may use inbound TCP, outbound connections or WebSocket depending on plugin and agent type. Prefer a supported authenticated, encrypted transport, least-privilege agent identities and private network paths. For WebSocket agents, ensure proxy upgrade headers and timeouts are correct. Do not expose agent listener ports without an approved threat model.

## 10. SSO and authentication callbacks

SSO integrations depend on exact redirect URIs, canonical Jenkins URL, IdP metadata, clock synchronization, trusted TLS and cookie behavior. Keep an audited break-glass recovery method; never disable authentication as a troubleshooting shortcut.

## 11. Monitoring and access audit

Measure ingress 4xx/5xx, proxy upstream latency, TLS expiry, authentication failures, webhook delivery, Jenkins HTTP availability, agent connection failures and controller JVM/queue metrics. Avoid logging Authorization headers, webhook secrets or session cookies.

## 12. Twenty troubleshooting scenarios

| # | Symptom | Diagnosis | Safe remediation |
|---|---|---|---|
| 1 | Proxy returns 502 | Check Jenkins process, upstream address and port | Restore healthy upstream |
| 2 | Proxy returns 504 | Inspect upstream latency, GC and timeout | Fix controller bottleneck; tune bounded timeouts |
| 3 | HTTP redirect loop | Check TLS termination, X-Forwarded-Proto and Jenkins URL | Correct trusted forwarded headers |
| 4 | Mixed-content warning | Inspect absolute HTTP links and root URL | Set canonical HTTPS URL |
| 5 | Webhook 403 | Check signature, auth, CSRF expectations and plugin endpoint | Repair signed webhook flow |
| 6 | Webhook 404 | Inspect path and plugin endpoint | Correct URL and installed integration |
| 7 | SSO callback mismatch | Compare IdP redirect URI, root URL and proxy headers | Correct canonical HTTPS callback |
| 8 | TLS certificate expired | Check cert dates and chain | Renew via approved CA workflow |
| 9 | Incomplete certificate chain | Inspect openssl s_client output | Install correct chain |
| 10 | DNS points to old proxy | Inspect dig and authoritative records | Update DNS and validate propagation |
| 11 | Backend exposed publicly | Inspect listeners, Docker port and firewall | Bind loopback/private and restrict network |
| 12 | X-Forwarded-For spoofing | Inspect proxy trust chain | Strip client headers and set trusted proxy values |
| 13 | WebSocket agent connection fails | Inspect Upgrade/Connection headers and proxy timeout | Enable approved WebSocket upgrade |
| 14 | Agent inbound port blocked | Inspect agent transport and firewall | Use supported secure transport |
| 15 | Large artifact upload fails | Inspect request limits and ingress buffering | Adjust reviewed limits or use artifact registry |
| 16 | Proxy request body timeout | Inspect logs and upstream metrics | Fix network/backend and bounded timeouts |
| 17 | Proxy path prefix wrong | Inspect Jenkins context path and proxy rewrite | Align context path and root URL |
| 18 | Authentication cookie insecure | Inspect Set-Cookie over HTTPS | Enforce secure HTTPS session handling |
| 19 | Rate limiting blocks webhooks | Inspect ingress policy and provider source | Tune verified provider-specific policy |
| 20 | Controller overload | Inspect queue, heap/GC, thread and HTTP metrics | Scale agents, remediate controller bottleneck |

## 13. Eight SRE runbooks

### RB-01 TLS certificate incident

**Procedure:** Check DNS, expiry, chain, TLS version and proxy reload; renew through approved CA and verify HTTPS.

**Exit criteria:** trusted HTTPS, authenticated UI, correct redirects, functioning webhooks and agent connectivity, private backend, audit evidence.

### RB-02 Proxy upstream outage

**Procedure:** Check Jenkins service, listener, proxy logs and health; restore upstream and validate login.

**Exit criteria:** trusted HTTPS, authenticated UI, correct redirects, functioning webhooks and agent connectivity, private backend, audit evidence.

### RB-03 Redirect/SSO loop

**Procedure:** Compare canonical root URL, IdP callback, forwarded headers and trusted proxy chain.

**Exit criteria:** trusted HTTPS, authenticated UI, correct redirects, functioning webhooks and agent connectivity, private backend, audit evidence.

### RB-04 Webhook delivery outage

**Procedure:** Inspect provider deliveries, signatures, endpoint permissions, proxy and Jenkins plugin logs.

**Exit criteria:** trusted HTTPS, authenticated UI, correct redirects, functioning webhooks and agent connectivity, private backend, audit evidence.

### RB-05 Agent transport outage

**Procedure:** Inspect agent protocol, WebSocket upgrade, proxy timeouts, certificates and connectivity.

**Exit criteria:** trusted HTTPS, authenticated UI, correct redirects, functioning webhooks and agent connectivity, private backend, audit evidence.

### RB-06 Network exposure incident

**Procedure:** Restrict public backend access, audit firewall/listeners and rotate any potentially exposed credentials.

**Exit criteria:** trusted HTTPS, authenticated UI, correct redirects, functioning webhooks and agent connectivity, private backend, audit evidence.

### RB-07 Proxy performance regression

**Procedure:** Correlate ingress latency with JVM/GC, thread pools, queue, upstream response and request limits.

**Exit criteria:** trusted HTTPS, authenticated UI, correct redirects, functioning webhooks and agent connectivity, private backend, audit evidence.

### RB-08 Change/rollback acceptance

**Procedure:** Test TLS, auth, webhooks, agents, metrics and rollback on staging; record owners and approval.

**Exit criteria:** trusted HTTPS, authenticated UI, correct redirects, functioning webhooks and agent connectivity, private backend, audit evidence.

## 14. Acceptance gates

| Gate | Requirement |
|---|---|
| G1 | Backend is loopback/private, not publicly exposed |
| G2 | Canonical HTTPS root URL configured for production |
| G3 | Certificate chain and renewal plan verified |
| G4 | Forwarded headers sanitized by trusted proxy |
| G5 | SSO/authentication and least privilege reviewed |
| G6 | Webhook signatures and plugin endpoints validated |
| G7 | Agent transport and WebSocket behavior documented |
| G8 | Proxy and Jenkins metrics/alerts defined |
| G9 | Three incident scenarios and rollback rehearsed |
| G10 | Lab cleanup and evidence complete |

## 15. Assessment — 100 points

| Domain | Points |
|---|---:|
| Architecture and private backend | 20 |
| HTTPS, TLS and proxy configuration | 20 |
| Jenkins URL, authentication and SSO | 15 |
| Webhook and agent networking | 15 |
| Troubleshooting and monitoring | 20 |
| Cleanup and evidence | 10 |
| **Total** | **100** |

**Pass:** 90+ with mandatory security gates; exposing a raw Jenkins backend or disabling TLS/authentication is an automatic fail.

## 16. Cleanup

```bash
docker stop jenkins-ch009
docker rm jenkins-ch009
# Destructive: only after confirming this volume is exclusively lab-owned.
docker volume rm jenkins-ch009-home
```

**Next:** Chapter 010 — Jenkins Installation, Configuration and Administration Production Readiness Capstone.
