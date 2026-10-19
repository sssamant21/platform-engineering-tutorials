# Chapter 091 — Enterprise Observability Security Architecture, Identity, RBAC and Tenant Isolation

**Part 19 — Enterprise Security, Governance and Reliability (1/5)**

## Mission

Build an auditable zero-trust security model for Prometheus, Alertmanager, Grafana, OpenTelemetry, Loki and Tempo across Kubernetes, data platforms and DBRE operations. Separate authentication, authorization, tenant enforcement and sensitive-data handling; no single header or dashboard permission is a complete security boundary.

## Reference security architecture

```text
Humans -> enterprise IdP (OIDC/SAML) -> Grafana RBAC -> datasource permissions
Workloads -> workload identity -> OTel gateway (TLS + authentication)
                                      |
                         policy + redaction + routing
                           /           |          \
                  Prometheus          Loki        Tempo
                       |                |            |
               authorized query    tenant ACLs    tenant ACLs
                       \                |            /
                        audit + SIEM + incident response
                           |
                    object store IAM / KMS
```

## Trust boundaries and threat modeling

Map the actors: developer, on-call SRE, DBRE, application, collector, CI service, Grafana, backend, object store and security reviewer. Identify attack paths: leaked service-account tokens, spoofed tenant headers, untrusted exporters, open scrape endpoints, plaintext OTLP, overly broad Grafana datasources, alert receiver secrets and cross-tenant log/trace access. Use defense in depth at ingress proxies, workload identity, backend tenancy and network policy.

## Identity and access controls

Use enterprise SSO with short-lived sessions and least-privilege Grafana roles. Review organization/folder/dashboard and datasource permissions independently. Kubernetes RBAC should grant collectors only required list/watch/get permissions; use separate service accounts by namespace and environment. Protect Prometheus APIs and remote-write receivers behind authenticated ingress; do not assume native Prometheus alone provides comprehensive multi-tenancy. Secure Alertmanager APIs, silence permissions and outbound webhook credentials.

## Loki and Tempo isolation

Do not trust a client-supplied tenant header without an authenticating gateway that maps verified identity to authorized tenant. In Loki, tenancy commonly uses `X-Scope-OrgID`; protect it at the ingress boundary. Tempo multitenancy behavior is deployment/version dependent: validate configuration, gateway enforcement and storage/query isolation. Test cross-tenant reads with dedicated synthetic tenants, never real customer data.

## OpenTelemetry data protection

Configure OTLP over TLS; use mTLS when the deployment supports and requires it. Keep certificates and exporter tokens in an approved secret manager and rotate with overlapping validity. Apply sensitive-data redaction before telemetry leaves the trusted zone. Scrub PostgreSQL SQL literals, Redis keys, Kafka message payloads, Elasticsearch document content, Snowflake query text and identifiers. Ensure trace attributes and metric labels are reviewed alongside logs.

## Kubernetes and storage defense

Use restrictive network policies, workload identity, immutable pinned images, restricted security contexts and scoped object-store IAM. Audit KMS encryption and bucket access. Ensure collector pipelines cannot export arbitrary telemetry to unapproved external destinations. Define emergency break-glass expiry, approval and post-use audit.

## Example Kubernetes network policy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: otel-gateway-ingress
  namespace: observability
spec:
  podSelector:
    matchLabels:
      app: otel-gateway
  policyTypes: [Ingress]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              observability-client: "true"
      ports:
        - protocol: TCP
          port: 4317
```

This example restricts ingress only; review egress separately, and confirm that the cluster CNI enforces NetworkPolicy. A namespace label alone does not authenticate the sender.

## Staging security acceptance

1. Verify IdP group-to-role mapping and datasource access.
2. Confirm workload tokens cannot read secrets or namespaces beyond their scope.
3. Test tenant A cannot query synthetic tenant B logs or traces.
4. Attempt unauthorized access to Prometheus/Alertmanager APIs.
5. Rotate a collector credential and verify uninterrupted delivery.
6. Simulate expired certificates and confirm alerts, fallback and recovery.
7. Inject synthetic sensitive fields and verify redaction before storage.
8. Preserve UTC audit events and approved rollback evidence.

## Offline executable security evidence gate

Save as `healthy.json`:

```json
{
  "owner": "observability-security-sre",
  "environment": "staging",
  "change_id": "OBS-091",
  "reviewed": true,
  "tenant_tested": true,
  "revocation_tested": true,
  "destructive_action": false,
  "checks": {
    "threat_model": true,
    "oidc": true,
    "grafana_rbac": true,
    "datasource_acl": true,
    "k8s_rbac": true,
    "workload_identity": true,
    "prometheus_auth": true,
    "alertmanager_acl": true,
    "loki_tenant": true,
    "tempo_tenant": true,
    "otlp_tls": true,
    "mtls": true,
    "secret_rotation": true,
    "object_iam": true,
    "log_redaction": true,
    "span_redaction": true,
    "metric_privacy": true,
    "network_policy": true,
    "audit": true,
    "break_glass": true,
    "incident_test": true,
    "rollback": true
  }
}
```

Save as `security_gate.py`:

```python
"""Offline synthetic security acceptance evidence gate; no external calls."""
import json,sys
from pathlib import Path
CHECKS=["threat_model","oidc","grafana_rbac","datasource_acl","k8s_rbac","workload_identity","prometheus_auth","alertmanager_acl","loki_tenant","tempo_tenant","otlp_tls","mtls","secret_rotation","object_iam","log_redaction","span_redaction","metric_privacy","network_policy","audit","break_glass","incident_test","rollback"]
def validate(p):
 if not isinstance(p,dict):return ["expected object"]
 e=[]
 for k in ("owner","change_id"):
  if not isinstance(p.get(k),str) or not p[k].strip():e.append("missing "+k)
 if p.get("environment") not in ("lab","staging"):e.append("unsafe environment")
 for k in ("reviewed","tenant_tested","revocation_tested"):
  if p.get(k) is not True:e.append("missing "+k)
 c=p.get("checks")
 if not isinstance(c,dict):e.append("invalid checks");c={}
 for k in CHECKS:
  if c.get(k) is not True:e.append("unverified "+k)
 if p.get("destructive_action") is not False:e.append("unsafe action")
 return e
if __name__=="__main__":
 try:p=json.loads(Path(sys.argv[1]).read_text());e=validate(p)
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not e else "FAIL","findings":e},indent=2));sys.exit(bool(e))

```

Save as `test_security_gate.py`:

```python
import copy,json,unittest
from pathlib import Path
from security_gate import validate
class SecurityTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_negative_01(self):
  p=copy.deepcopy(self.p)
  p["checks"]["threat_model"]=False
  self.assertTrue(validate(p))
 def test_negative_02(self):
  p=copy.deepcopy(self.p)
  p["checks"]["oidc"]=False
  self.assertTrue(validate(p))
 def test_negative_03(self):
  p=copy.deepcopy(self.p)
  p["checks"]["grafana_rbac"]=False
  self.assertTrue(validate(p))
 def test_negative_04(self):
  p=copy.deepcopy(self.p)
  p["checks"]["datasource_acl"]=False
  self.assertTrue(validate(p))
 def test_negative_05(self):
  p=copy.deepcopy(self.p)
  p["checks"]["k8s_rbac"]=False
  self.assertTrue(validate(p))
 def test_negative_06(self):
  p=copy.deepcopy(self.p)
  p["checks"]["workload_identity"]=False
  self.assertTrue(validate(p))
 def test_negative_07(self):
  p=copy.deepcopy(self.p)
  p["checks"]["prometheus_auth"]=False
  self.assertTrue(validate(p))
 def test_negative_08(self):
  p=copy.deepcopy(self.p)
  p["checks"]["alertmanager_acl"]=False
  self.assertTrue(validate(p))
 def test_negative_09(self):
  p=copy.deepcopy(self.p)
  p["checks"]["loki_tenant"]=False
  self.assertTrue(validate(p))
 def test_negative_10(self):
  p=copy.deepcopy(self.p)
  p["checks"]["tempo_tenant"]=False
  self.assertTrue(validate(p))
 def test_negative_11(self):
  p=copy.deepcopy(self.p)
  p["checks"]["otlp_tls"]=False
  self.assertTrue(validate(p))
 def test_negative_12(self):
  p=copy.deepcopy(self.p)
  p["checks"]["mtls"]=False
  self.assertTrue(validate(p))
 def test_negative_13(self):
  p=copy.deepcopy(self.p)
  p["checks"]["secret_rotation"]=False
  self.assertTrue(validate(p))
 def test_negative_14(self):
  p=copy.deepcopy(self.p)
  p["checks"]["object_iam"]=False
  self.assertTrue(validate(p))
 def test_negative_15(self):
  p=copy.deepcopy(self.p)
  p["checks"]["log_redaction"]=False
  self.assertTrue(validate(p))
 def test_negative_16(self):
  p=copy.deepcopy(self.p)
  p["checks"]["span_redaction"]=False
  self.assertTrue(validate(p))
 def test_negative_17(self):
  p=copy.deepcopy(self.p)
  p["checks"]["metric_privacy"]=False
  self.assertTrue(validate(p))
 def test_negative_18(self):
  p=copy.deepcopy(self.p)
  p["checks"]["network_policy"]=False
  self.assertTrue(validate(p))
 def test_negative_19(self):
  p=copy.deepcopy(self.p)
  p["checks"]["audit"]=False
  self.assertTrue(validate(p))
 def test_negative_20(self):
  p=copy.deepcopy(self.p)
  p["checks"]["break_glass"]=False
  self.assertTrue(validate(p))
 def test_negative_21(self):
  p=copy.deepcopy(self.p)
  p["checks"]["incident_test"]=False
  self.assertTrue(validate(p))
 def test_negative_22(self):
  p=copy.deepcopy(self.p)
  p["checks"]["rollback"]=False
  self.assertTrue(validate(p))
 def test_negative_23(self):
  p=copy.deepcopy(self.p)
  p["owner"]=""
  self.assertTrue(validate(p))
 def test_negative_24(self):
  p=copy.deepcopy(self.p)
  p["change_id"]=""
  self.assertTrue(validate(p))
 def test_negative_25(self):
  p=copy.deepcopy(self.p)
  p["environment"]="production"
  self.assertTrue(validate(p))
 def test_negative_26(self):
  p=copy.deepcopy(self.p)
  p["reviewed"]=false
  self.assertTrue(validate(p))
 def test_negative_27(self):
  p=copy.deepcopy(self.p)
  p["tenant_tested"]=false
  self.assertTrue(validate(p))
 def test_negative_28(self):
  p=copy.deepcopy(self.p)
  p["revocation_tested"]=false
  self.assertTrue(validate(p))
 def test_negative_29(self):
  p=copy.deepcopy(self.p)
  p["destructive_action"]=true
  self.assertTrue(validate(p))
 def test_negative_30(self):
  p=copy.deepcopy(self.p)
  p["checks"]=null
  self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
python3 security_gate.py healthy.json
python3 -m unittest -v test_security_gate.py
```

Expected PASS and **32 authored tests**. The offline gate validates synthetic evidence flags only, not actual isolation; live execution remains pending.

## 24 hands-on exercises

1. Threat-model telemetry ingress: identify trust boundary, implement safe staging check, capture evidence and rollback.
2. Inventory identities: identify trust boundary, implement safe staging check, capture evidence and rollback.
3. Define trust boundaries: identify trust boundary, implement safe staging check, capture evidence and rollback.
4. Configure OIDC SSO: identify trust boundary, implement safe staging check, capture evidence and rollback.
5. Review Grafana roles: identify trust boundary, implement safe staging check, capture evidence and rollback.
6. Review datasource permissions: identify trust boundary, implement safe staging check, capture evidence and rollback.
7. Review Kubernetes RBAC: identify trust boundary, implement safe staging check, capture evidence and rollback.
8. Review workload identity: identify trust boundary, implement safe staging check, capture evidence and rollback.
9. Restrict Prometheus scrape credentials: identify trust boundary, implement safe staging check, capture evidence and rollback.
10. Enforce Alertmanager receiver ACLs: identify trust boundary, implement safe staging check, capture evidence and rollback.
11. Protect Loki tenant headers: identify trust boundary, implement safe staging check, capture evidence and rollback.
12. Enforce Tempo tenant access: identify trust boundary, implement safe staging check, capture evidence and rollback.
13. Require TLS on OTLP: identify trust boundary, implement safe staging check, capture evidence and rollback.
14. Require mTLS where supported: identify trust boundary, implement safe staging check, capture evidence and rollback.
15. Rotate collector secrets: identify trust boundary, implement safe staging check, capture evidence and rollback.
16. Validate object-store IAM: identify trust boundary, implement safe staging check, capture evidence and rollback.
17. Redact log sensitive fields: identify trust boundary, implement safe staging check, capture evidence and rollback.
18. Redact span attributes: identify trust boundary, implement safe staging check, capture evidence and rollback.
19. Limit metrics label leakage: identify trust boundary, implement safe staging check, capture evidence and rollback.
20. Configure network policies: identify trust boundary, implement safe staging check, capture evidence and rollback.
21. Audit security events: identify trust boundary, implement safe staging check, capture evidence and rollback.
22. Simulate cross-tenant query: identify trust boundary, implement safe staging check, capture evidence and rollback.
23. Test secret revocation: identify trust boundary, implement safe staging check, capture evidence and rollback.
24. Approve security acceptance: identify trust boundary, implement safe staging check, capture evidence and rollback.

## 24 production incident scenarios

1. **Stolen Grafana token:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
2. **Overprivileged dashboard editor:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
3. **Datasource cross-tenant access:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
4. **Kubernetes service account compromise:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
5. **Collector secret exposure:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
6. **Plaintext OTLP traffic:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
7. **Expired TLS certificate:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
8. **Spoofed tenant header:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
9. **Loki cross-tenant read:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
10. **Tempo trace disclosure:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
11. **Prometheus scrape credential leak:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
12. **Alertmanager webhook token leak:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
13. **Object store public access:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
14. **Unrestricted network egress:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
15. **PII in metric labels:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
16. **PII in logs:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
17. **PII in spans:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
18. **Missing audit event:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
19. **Unauthorized silence:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
20. **OIDC outage:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
21. **RBAC drift:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
22. **Secret rotation outage:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
23. **Supply-chain image compromise:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.
24. **Break-glass misuse:** identify exposure scope, contain access, preserve audit trail, recover and prevent recurrence.

## Eight production runbooks

1. **Identity compromise and token revocation:** define trigger, on-call owner, authorization, containment, validation and audit evidence.
2. **Grafana RBAC and datasource isolation investigation:** define trigger, on-call owner, authorization, containment, validation and audit evidence.
3. **Loki and Tempo tenant-boundary incident:** define trigger, on-call owner, authorization, containment, validation and audit evidence.
4. **OpenTelemetry TLS and secrets rotation:** define trigger, on-call owner, authorization, containment, validation and audit evidence.
5. **Sensitive telemetry detection and containment:** define trigger, on-call owner, authorization, containment, validation and audit evidence.
6. **Kubernetes RBAC, network policy and workload identity:** define trigger, on-call owner, authorization, containment, validation and audit evidence.
7. **Object storage access incident and audit evidence:** define trigger, on-call owner, authorization, containment, validation and audit evidence.
8. **Break-glass access, restoration and post-incident review:** define trigger, on-call owner, authorization, containment, validation and audit evidence.

## 100-point security assessment

| Domain | Points |
|---|---:|
| Identity, SSO and Grafana RBAC | 20 |
| Workload identity, network and API access | 20 |
| Loki/Tempo tenant isolation | 20 |
| TLS, secrets, privacy and storage | 20 |
| Incident response, evidence and recovery | 20 |
| **Total** | **100** |

Recommended passing score 85/100 with no critical cross-tenant or sensitive-data exposures. Require witnessed staging isolation and token revocation tests before production approval.

**Companion:** [Chapter 091 lab](labs/091-enterprise-observability-security-architecture-identity-rbac-tenant-isolation-lab.md).

**Next:** Chapter 092 — Observability Data Governance, Privacy, Retention, Encryption and Audit Compliance.
