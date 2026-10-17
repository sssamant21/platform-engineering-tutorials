# Chapter 094 — Jenkins Enterprise Security, Compliance and Operational Risk Management

**Part 19 — Enterprise Jenkins SRE Operations and FinOps**  
**Audience:** Jenkins SRE/DBRE, platform security, DevSecOps, auditors, incident responders and change owners.  
**Prerequisites:** Chapters 056–065 and 091–093; Python 3, Git, Jenkins staging controller (optional).

## Learning objectives

Design a Jenkins security control framework, manage identity and supply-chain risk, map evidence to audit requirements, track exceptions, prioritize vulnerabilities and implement repeatable policy tests without exposing production credentials.

## 1. Threat model and trust boundaries

```text
Developers / SCM / PRs
          |
   webhook + repo trust
          |
 Jenkins controller ── plugins / JCasC / RBAC / credentials
          |
      build agents ── toolchains / containers / workspace
          |
 artifacts / registries / signing / deployment identities
          |
 production systems, data stores, Kubernetes and cloud APIs
```

Assume Jenkinsfiles and pull requests may contain attacker-controlled code. Build agents should be isolated from the controller and from other trust tiers. Never grant production deployment secrets to untrusted PR jobs.

## 2. Control ownership

| Domain | Key controls | Accountable owner |
|---|---|---|
| Identity | SSO, MFA, RBAC, service accounts | Security + platform |
| Controller | LTS/Java support, hardened endpoints, TLS | Platform SRE |
| Plugins | allowlist, pinned versions, advisories | Platform SRE |
| Pipeline | code review, sandbox, untrusted PR isolation | Pipeline owner |
| Agent | ephemeral identity, filesystem isolation, no privileged builds by default | Platform |
| Secrets | external manager, scoped credentials, rotation, no logs | Security |
| Supply chain | signed provenance, SBOM, artifact integrity | DevSecOps |
| Audit | immutable evidence, retention, change approval | Compliance |
| Recovery | encrypted backups, restore test, single-writer | Platform/Infra |
| Risk | severity, exception expiration, remediation owner | Service owner |

Define the actual RACI and policy versions for your organization; the table is a reference architecture.

## 3. Identity and authorization

- Prefer enterprise IdP SSO, MFA and group-to-role mapping.
- Review Jenkins administrator, Job/Configure, Credentials/View and Agent/Configure permissions.
- Apply folder-level authorization and environment isolation for high-risk pipelines.
- Prefer OIDC or workload identity to long-lived cloud keys.
- Restrict service accounts, webhook tokens and API tokens; rotate and revoke orphaned credentials.
- Require break-glass access logging, time limits, independent approval and post-use review.

## 4. Controller and agent hardening

- Use supported Jenkins LTS, Java and plugin versions; test compatibility before upgrading.
- Restrict controller network ingress and access to administrative endpoints.
- Disable anonymous administration and avoid building on the controller.
- Use ephemeral agents, dedicated namespaces/node pools and least-privilege Kubernetes service accounts.
- Limit privileged containers, host mounts and host Docker socket exposure.
- Protect JENKINS_HOME permissions, backups and restore encryption keys.
- Avoid exposing credentials in shell tracing, pipeline logs, archived artifacts or shared workspaces.

## 5. Pipeline supply-chain security

```text
SCM commit → branch protection → trusted pipeline definition
    → pinned build environment → dependency verification
    → SAST/SCA/secrets/IaC scans → artifact/SBOM/provenance
    → signature verification → deployment approval
```

A green scan is not proof of zero vulnerabilities. Keep provenance linked to source commit, builder identity and immutable artifact digest. Treat artifact signing keys as privileged production identities.

## 6. Security evidence and compliance mapping

Use control IDs and evidence rather than asserting compliance solely because a pipeline passed.

| Control ID | Requirement | Example evidence |
|---|---|---|
| IAM-01 | SSO and MFA enforced | IdP policy and access review |
| IAM-02 | least-privilege RBAC | permission matrix |
| SEC-01 | supported Jenkins and plugins | version inventory/advisory review |
| SEC-02 | secrets protected and rotated | secret manager audit |
| CICD-01 | protected PR and trusted CI | branch settings/build logs |
| CICD-02 | artifact provenance verified | digest/signature/SBOM |
| OPS-01 | approved changes | change ticket and approvals |
| OPS-02 | backup restore proven | DR exercise |
| AUD-01 | logs and evidence retained | retention policy and sample |
| RISK-01 | exceptions have owners/expiry | risk register |

SOC 2, HIPAA, ISO 27001 and similar frameworks require organization-specific scope, interpretation and independent assessment; this chapter provides engineering evidence patterns, not certification.

## 7. Risk scoring and remediation policy

Example scoring model (not a replacement for CVSS, EPSS or business impact analysis):

```text
risk_score = impact × likelihood
impact, likelihood ∈ [1, 5]
```

| Score | Classification | Action |
|---|---|---|
| 1–4 | Low | planned backlog |
| 5–9 | Medium | scheduled remediation |
| 10–16 | High | prioritized change and owner |
| 17–25 | Critical | immediate security review and mitigation |

Record vulnerability/advisory source, affected asset, exposure, exploitability, compensating controls, owner, due date, status, approval and expiry. Do not automatically restart Jenkins or remove plugins based only on a score.

## 8. Executable offline security policy validator

Save `policy/jenkins-security.json`:

```json
{
  "controller": {
    "anonymous_admin": false,
    "controller_build_executors": 0,
    "tls_enabled": true,
    "backups_encrypted": true
  },
  "identity": {
    "sso_enabled": true,
    "mfa_required": true,
    "service_account_reviewed": true
  },
  "pipeline": {
    "untrusted_pr_has_prod_secrets": false,
    "privileged_agents_default": false,
    "artifact_provenance_required": true
  },
  "governance": {
    "change_approval_required": true,
    "audit_retention_defined": true,
    "risk_owner": "platform-security"
  }
}
```

Save `scripts/security_gate.py`:

```python
#!/usr/bin/env python3
import json
import sys
from pathlib import Path

REQUIRED = {
    "controller.anonymous_admin": False,
    "controller.controller_build_executors": 0,
    "controller.tls_enabled": True,
    "controller.backups_encrypted": True,
    "identity.sso_enabled": True,
    "identity.mfa_required": True,
    "identity.service_account_reviewed": True,
    "pipeline.untrusted_pr_has_prod_secrets": False,
    "pipeline.privileged_agents_default": False,
    "pipeline.artifact_provenance_required": True,
    "governance.change_approval_required": True,
    "governance.audit_retention_defined": True,
}

def validate(document):
    failures = []
    for dotted, expected in REQUIRED.items():
        group, key = dotted.split(".")
        value = document.get(group, {}).get(key)
        if type(value) is not type(expected) or value != expected:
            failures.append(f"{dotted}: expected {expected!r}, got {value!r}")
    owner = document.get("governance", {}).get("risk_owner")
    if not isinstance(owner, str) or not owner.strip():
        failures.append("governance.risk_owner: missing")
    return failures

if __name__ == "__main__":
    document = json.loads(Path(sys.argv[1]).read_text())
    failures = validate(document)
    if failures:
        print("SECURITY POLICY DENY", *failures, sep="\n")
        sys.exit(1)
    print("SECURITY POLICY ALLOW: synthetic declaration")
```

```bash
python3 scripts/security_gate.py policy/jenkins-security.json
```

**Important:** This validates a declared JSON fixture, not real Jenkins permissions, IdP MFA, agent isolation, secret-manager configuration or artifact signatures. Production acceptance requires authoritative API evidence and independent control tests.

## 9. Negative security tests

```bash
cp policy/jenkins-security.json /tmp/jenkins-security-unsafe.json
python3 - <<'PY'
import json
p = "/tmp/jenkins-security-unsafe.json"
with open(p) as f:
    d = json.load(f)
d["pipeline"]["untrusted_pr_has_prod_secrets"] = True
d["controller"]["anonymous_admin"] = True
with open(p, "w") as f:
    json.dump(d, f)
PY
if python3 scripts/security_gate.py /tmp/jenkins-security-unsafe.json; then
  echo "FAIL: unsafe declaration accepted"; exit 1
else
  echo "PASS: unsafe declaration denied"
fi
```

## 10. Jenkins validation Pipeline

```groovy
pipeline {
  agent { label 'security-validation' }
  options {
    timestamps()
    timeout(time: 10, unit: 'MINUTES')
  }
  stages {
    stage('Checkout') { steps { checkout scm } }
    stage('Security contract') {
      steps { sh 'python3 scripts/security_gate.py policy/jenkins-security.json' }
    }
  }
}
```

Run on trusted, pinned agents. Do not grant write credentials or production secrets to PR validation jobs.

## 11. Twenty security and compliance failure scenarios

| # | Symptom | Investigation |
|---|---|---|
| 01 | Anonymous admin access | security realm |
| 02 | Admin permission creep | RBAC |
| 03 | MFA not enforced | IdP policy |
| 04 | Orphaned API token | credential audit |
| 05 | Secret printed in log | masking/rotation |
| 06 | PR accesses production credential | trust boundary |
| 07 | Controller executes builds | executors |
| 08 | Privileged agent container | pod security |
| 09 | Host Docker socket exposed | mounts |
| 10 | Unsupported plugin | advisory |
| 11 | Plugin dependency conflict | compatibility |
| 12 | Unverified artifact | provenance |
| 13 | Missing SBOM | supply-chain gate |
| 14 | Jenkins backup unencrypted | storage |
| 15 | Restore keys unavailable | DR |
| 16 | Audit logs deleted early | retention |
| 17 | Unapproved change | change records |
| 18 | Expired risk exception | register |
| 19 | Security alert not routed | on-call |
| 20 | Compromised CI identity | revoke/forensics |

## 12. Six production security runbooks

### A. Suspected Jenkins credential compromise
Restrict affected identities, preserve audit trail, rotate/revoke secrets, inspect builds and downstream cloud actions, and coordinate security response.

### B. Critical Jenkins/plugin vulnerability
Determine exposure and exploitability, isolate if needed, validate compatible fix in staging, approve change and verify no regressions.

### C. Untrusted PR crosses secret boundary
Disable affected job/credential scope, rotate exposed secrets, inspect logs/artifacts, fix trust policy and verify negative tests.

### D. RBAC/SSO incident
Use audited break-glass path, verify IdP and Jenkins permissions, restore least privilege and complete post-use review.

### E. Supply-chain artifact integrity failure
Block promotion, quarantine artifacts, inspect provenance, rebuild from trusted source and rotate signing identity if compromised.

### F. Audit or exception failure
Preserve available evidence, identify control gap, assign accountable owner, document time-bound mitigation and verify closure.

## 13. 100-point acceptance

| Domain | Points |
|---|---:|
| Identity, SSO/MFA and RBAC | 20 |
| Controller, plugin and agent hardening | 20 |
| Secrets and CI trust boundaries | 20 |
| Supply-chain security and provenance | 15 |
| Risk register and audit evidence | 15 |
| Tests, incident runbooks and sign-off | 10 |
| **Total** | **100** |

Suggested pass 85/100 plus mandatory gates: no anonymous administration, no production secrets in untrusted PRs, least-privilege agents, approved credential ownership, critical vulnerability review and auditable emergency access. Unverified controls remain blocked.

## 14. Evidence template

```text
UTC / service / environment:
Jenkins core/Java/plugin inventory:
SSO/MFA and RBAC access review:
Controller/agent hardening:
Credentials/rotation/secret manager:
PR trust and pipeline scan:
SBOM/provenance/signature:
Backup encryption/restore:
Audit retention and exception register:
20 scenarios / six runbooks:
Score / RCA / COA / reviewer:
```

**Companion:** [Chapter 094 hands-on lab](labs/094-jenkins-enterprise-security-compliance-operational-risk-management-check.md).  
**Next:** Chapter 095 — Jenkins Enterprise SRE Operations, Security and FinOps Acceptance Capstone.
