# Chapter 098 — Hands-on Lab: Enterprise Jenkins Failure Injection and DR

**Safety:** Synthetic offline failure simulation; no destructive chaos commands or production changes.

## 24 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Define service impact | Tier |
| 02 | Assign incident command | RACI |
| 03 | Map failure domains | Diagram |
| 04 | Baseline SLO/error budget | Dashboard |
| 05 | Define RTO/RPO | Contract |
| 06 | Review backup/key custody | Evidence |
| 07 | Define isolated restore | Plan |
| 08 | Define single-writer fencing | Gate |
| 09 | Define blast radius | Scope |
| 10 | Obtain drill approval | Ticket |
| 11 | Simulate controller failure | Tabletop |
| 12 | Simulate agent outage | Tabletop |
| 13 | Simulate storage latency | Tabletop |
| 14 | Simulate SCM outage | Tabletop |
| 15 | Simulate registry outage | Tabletop |
| 16 | Simulate IdP failure | Tabletop |
| 17 | Simulate plugin rollback | Tabletop |
| 18 | Practice communications | Timeline |
| 19 | Calculate RTO/RPO | Output |
| 20 | Define critical CI validation | Contract |
| 21 | Define artifact/RBAC checks | Checklist |
| 22 | Run validator and tests | Results |
| 23 | Run unsafe negative fixture | Denial |
| 24 | Score and publish COA | Review |

## 12 failure drills

1. Unapproved game day.
2. Missing rollback.
3. Dual controller writers.
4. Missing backup.
5. Corrupted restore.
6. RTO breach.
7. RPO breach.
8. Agent Pending.
9. SCM webhook outage.
10. Artifact digest mismatch.
11. IdP credential failure.
12. Failed synthetic CI after recovery.

## Executable synthetic checks

Use `data/drill.json`, `scripts/drill_check.py` and `tests/test_drill.py` from the main chapter:

```bash
python3 scripts/drill_check.py data/drill.json
python3 -m unittest discover -s tests -v
cp data/drill.json /tmp/jenkins-drill-unsafe.json
python3 - <<'PY'
import json
p = "/tmp/jenkins-drill-unsafe.json"
with open(p) as f:
    d = json.load(f)
d["approved"] = False
d["single_writer_verified"] = False
d["recovered_at"] = "2026-10-17T11:00:00Z"
with open(p, "w") as f:
    json.dump(d, f)
PY
if python3 scripts/drill_check.py /tmp/jenkins-drill-unsafe.json; then
  echo "FAIL: unsafe drill accepted"; exit 1
else
  echo "PASS: unsafe drill denied"
fi
```

## DR tabletop

A Jenkins controller becomes unavailable during a release. The original controller's storage status is uncertain, the most recent backup is 10 minutes old and the business RTO is 30 minutes. Require explicit fencing before restore, inspect backup consistency and key custody, validate isolated recovery, and decide go/no-go from critical CI, RBAC, artifact integrity and measured RTO/RPO.

## Evidence worksheet

```text
UTC / lab owner:
Scope and approval:
SLO/error budget:
Backup/fencing:
Synthetic RTO/RPO:
Incident command:
Critical CI/artifact/RBAC:
Validator and tests:
12 failure drills:
Score / RCA / COA / reviewer:
```

## Acceptance

- [ ] 24 exercises attempted with evidence.
- [ ] 12 failure drills completed or explicitly blocked.
- [ ] Scope, approvals and stop conditions documented.
- [ ] Backup, encryption keys and single-writer design reviewed.
- [ ] RTO/RPO calculations independently checked.
- [ ] Incident communication and recovery acceptance defined.
- [ ] Validator and tests executed.
- [ ] Unsafe fixture denied.
- [ ] Real recovery gates clearly marked unverified until staging drill.
- [ ] Reviewer sign-off recorded.

**Related:** [Chapter 098 — Jenkins Enterprise Failure Injection, Incident Recovery and Disaster Recovery Capstone](../098-jenkins-enterprise-failure-injection-incident-recovery-disaster-recovery-capstone.md).
