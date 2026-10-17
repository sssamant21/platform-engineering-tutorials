# Chapter 091 — Hands-on Lab: Jenkins Enterprise SRE Operating Model and Governance

**Safety:** Offline Python/Git lab; optional read-only Jenkins staging review. Do not change production RBAC, backup or on-call routes during this exercise.

## 20 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Define Jenkins platform service boundary | Diagram |
| 02 | Identify business owner | Catalog |
| 03 | Identify platform owner | Catalog |
| 04 | Identify pipeline owners | RACI |
| 05 | Assign tier and impact | Tier decision |
| 06 | Record on-call escalation | Route |
| 07 | Define UI/API availability SLI | Specification |
| 08 | Define queue latency SLI | Specification |
| 09 | Define agent provisioning SLI | Specification |
| 10 | Calculate 30-day error budget | Calculation |
| 11 | Define error-budget action policy | Policy |
| 12 | Record RTO/RPO | Catalog |
| 13 | Review restore evidence | Report |
| 14 | Review core/plugin/Java lifecycle | Matrix |
| 15 | Review access and secret ownership | Checklist |
| 16 | Attribute controller/agent cost | Model |
| 17 | Create service catalog JSON | File |
| 18 | Execute catalog validator | Result |
| 19 | Simulate missing owner or bad tier | Failure |
| 20 | Score 100-point acceptance and COA | Sign-off |

## 12 failure drills

1. Missing platform owner.
2. Missing business owner.
3. No on-call route.
4. Unsupported service tier.
5. Duplicate service ID.
6. Invalid RTO.
7. Invalid RPO.
8. Invalid SLO.
9. Missing DR runbook.
10. Invalid restore-test date.
11. Error budget exhausted.
12. Cost center missing.

## Executable validator

Use the `catalog/jenkins-services.json` and `scripts/validate_catalog.py` files from the main chapter.

```bash
python3 scripts/validate_catalog.py catalog/jenkins-services.json
cp catalog/jenkins-services.json /tmp/jenkins-governance-invalid.json
python3 - <<'PY'
import json
p = "/tmp/jenkins-governance-invalid.json"
doc = json.load(open(p))
doc["services"][0]["platform_owner"] = ""
doc["services"][0]["rto_minutes"] = -1
with open(p, "w") as f:
    json.dump(doc, f)
PY
if python3 scripts/validate_catalog.py /tmp/jenkins-governance-invalid.json; then
  echo "FAIL: invalid catalog accepted"; exit 1
else
  echo "PASS: invalid catalog rejected"
fi
```

## SLO budget lab

For a 30-day window:

```python
for target in (0.99, 0.999, 0.9995):
    budget_minutes = 30 * 24 * 60 * (1 - target)
    print(f"{target:.2%}: {budget_minutes:.2f} minutes")
```

Expected 99.9% = 43.2 minutes; 99.95% = 21.6 minutes. Real SLIs must specify exclusions, measurement and user impact.

## Incident tabletop

A production Jenkins controller is available, but critical pipelines wait 30 minutes in queue. Determine whether availability SLI alone is adequate, assign incident commander, identify agent capacity or quota bottlenecks, establish communications, preserve evidence and record COAs.

## Evidence worksheet

```text
UTC / lab owner:
Service ID and tier:
Business/platform/pipeline owners:
RACI and on-call escalation:
SLI/SLO/error budget:
RTO/RPO and restore evidence:
RBAC/credentials/lifecycle review:
Capacity and cost attribution:
Validator positive/negative tests:
12 failure drills:
Score / RCA / COA / reviewer:
```

## Acceptance

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or explicitly blocked.
- [ ] Service boundaries and RACI defined.
- [ ] Named owners and on-call route documented.
- [ ] SLO/error budget calculation reviewed.
- [ ] RTO/RPO and DR evidence identified.
- [ ] Catalog validator accepts valid input and rejects invalid input.
- [ ] Security and FinOps accountability reviewed.
- [ ] Incident tabletop completed.
- [ ] Reviewer sign-off recorded.

**Related:** [Chapter 091 — Jenkins Enterprise SRE Operating Model, Governance and Service Ownership](../091-jenkins-enterprise-sre-operating-model-governance-service-ownership.md).
