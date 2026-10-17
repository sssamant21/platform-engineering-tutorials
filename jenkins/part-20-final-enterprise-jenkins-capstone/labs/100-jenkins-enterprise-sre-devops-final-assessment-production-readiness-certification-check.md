# Chapter 100 — Final Hands-on Assessment Lab and Internal Readiness Record

**Scope:** Self-administered Jenkins enterprise SRE/DevOps final assessment. Offline fixture tests plus independently evidenced staging exercises. **Not an official Jenkins credential.**

## 24 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Architecture and trust boundaries | Diagram |
| 02 | Controller/agent single-writer safety | ADR |
| 03 | SCM branch/webhook security | Policy |
| 04 | Declarative Pipeline review | Pipeline |
| 05 | Shared library pinning | Version |
| 06 | Kubernetes agent isolation | Pod |
| 07 | JCasC/plugin/Java review | Matrix |
| 08 | SSO/MFA/RBAC review | Evidence |
| 09 | PR secret isolation | Gate |
| 10 | SBOM/provenance/digest | Artifact |
| 11 | Controller/agent observability | Dashboard |
| 12 | Critical-job SLI/SLO | Contract |
| 13 | Error-budget calculation | Worksheet |
| 14 | Queue incident tabletop | Timeline |
| 15 | Controller/agent failure tabletop | Response |
| 16 | Backup encryption and keys | Review |
| 17 | Restore and RTO/RPO | Evidence |
| 18 | Terraform state and plan | Review |
| 19 | Ansible/GitOps drift | Matrix |
| 20 | Executor forecast | Capacity |
| 21 | Cost allocation and reconciliation | FinOps |
| 22 | Run assessment script/tests | Results |
| 23 | Run unsafe negative fixture | Denial |
| 24 | RCA/COA and assessor sign-off | Record |

## 20 failure drills

1. Controller OOM.
2. Dual active writers.
3. Queue saturation.
4. Agent Pending.
5. Image pull error.
6. SCM webhook outage.
7. PR secret leak.
8. Vulnerable plugin.
9. JCasC incompatibility.
10. RBAC privilege creep.
11. Artifact digest mismatch.
12. Terraform state conflict.
13. Destructive drift.
14. Storage latency.
15. Failed restore.
16. RTO/RPO breach.
17. Missing burn alert.
18. Cost anomaly.
19. Rightsizing SLO regression.
20. Missing change approval.

## Executable final assessment

Use `assessment/final.json`, `scripts/final_assessment.py` and `tests/test_final_assessment.py` from the chapter:

```bash
python3 scripts/final_assessment.py assessment/final.json
python3 -m unittest discover -s tests -v
cp assessment/final.json /tmp/jenkins-final-unsafe.json
python3 - <<'PY'
import json
p = "/tmp/jenkins-final-unsafe.json"
with open(p) as f:
    d = json.load(f)
d["mandatory"]["single_writer_verified"] = False
d["mandatory"]["untrusted_pr_prod_secrets"] = True
d["score"]["written"] = 0
with open(p, "w") as f:
    json.dump(d, f)
PY
if python3 scripts/final_assessment.py /tmp/jenkins-final-unsafe.json; then
  echo "FAIL: unsafe assessment allowed"; exit 1
else
  echo "PASS: unsafe assessment denied"
fi
```

## Final review tabletop

A production Jenkins release is delayed by queue saturation, a critical plugin advisory and a cloud cost anomaly. Assess SLO burn, security exposure, capacity headroom, approval/rollback and communications. Provide go/no-go decision with evidence and assigned COAs.

## 100-point rubric

| Domain | Maximum |
|---|---:|
| Written assessment | 20 |
| Architecture | 15 |
| CI/CD and security | 15 |
| Observability/incidents/SLOs | 15 |
| Backup/DR | 15 |
| Capacity/FinOps | 10 |
| Evidence/sign-off | 10 |
| **Total** | **100** |

## Internal completion record

```text
Candidate / assessor / UTC:
Chapters reviewed:
Written score:
Architecture/CI/security evidence:
SLO and incident evidence:
Restore/RTO/RPO evidence:
Capacity/FinOps evidence:
Script positive/negative results:
24 labs and 20 drills:
Final score / mandatory gates:
GO/NO-GO:
RCA/COA:
Independent reviewer:
```

## Acceptance

- [ ] 30 written questions answered and scored.
- [ ] 24 exercises completed with evidence or blockers.
- [ ] 20 failure drills completed or explicitly blocked.
- [ ] Architecture and security reviewed.
- [ ] SLO and incident response reviewed.
- [ ] Isolated restore and RTO/RPO independently evidenced.
- [ ] Capacity and billing reconciliation reviewed.
- [ ] Positive fixture and unit tests executed.
- [ ] Unsafe fixture denied.
- [ ] All mandatory gates independently verified.
- [ ] Authorized assessor recorded outcome.

**Related:** [Chapter 100 — Jenkins Enterprise SRE/DevOps Final Assessment and Production Readiness Certification](../100-jenkins-enterprise-sre-devops-final-assessment-production-readiness-certification.md).

**Curriculum status:** All 100 chapters published. This lab does not itself award certification.
