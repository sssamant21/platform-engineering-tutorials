# Chapter 100 — Enterprise IaC FinOps and Reliability Acceptance Capstone

**Part 20 — FinOps | 100/120 | Enterprise SRE/DBRE**

> **Evidence boundary:** All included code is an offline synthetic acceptance simulator. It does not query cloud providers, execute Terraform, resize databases, or prove production acceptance. Native lab execution and independent acceptance are pending.

## Learning outcomes
Integrate Chapters 096–099 into a cost and reliability control plane: AWS CUR/Data Exports, Azure Cost Management, GCP BigQuery Billing, shared Kubernetes costs, invoice reconciliation, showback/chargeback, budget forecasting, anomaly response, commitment utilization, and DBRE-safe optimization.

## Enterprise architecture
```text
AWS / Azure / GCP billing exports
  -> immutable ingest, schema, currency and invoice tie-out
  -> cost-center and shared K8s allocation
  -> budget forecast and anomaly review
  -> rightsizing and commitment recommendation
  -> SLO, peak capacity, DBRE recovery and security gates
  -> Finance + SRE + DBRE approval
  -> Git PR -> IaC plan -> staging canary -> rollback drill
  -> authorized production change -> realized savings audit
```
Separate read-only billing access from deployment privileges. Never store credentials, tenant-sensitive exports or unredacted invoices in Git.

## Acceptance contracts
| Domain | Evidence | Fail-closed condition |
|---|---|---|
| Billing | source IDs, UTC period, currency, cost basis, invoice | duplicates, stale data, mismatch |
| Allocation | deterministic integer-cent cost-center ledger | unallocated shared spend |
| Forecast | holdout backtesting, bias, error and budget policy | missing history or unstable residuals |
| Optimization | comparable baseline, p95/p99, savings estimate | average CPU used alone |
| Commitments | eligibility, term, utilization and unused-risk | unapproved purchase |
| Kubernetes | PDB, HPA, requests, topology and N-1 capacity | evictions or failover risk |
| DBRE | replica/quorum, backups, restore, PITR, RPO/RTO | unverified recovery |
| Delivery | Git diff, state lock, plan, approvals, canary, rollback | destructive/unapproved change |
| Audit | evidence hash, owner, timestamp, invoice | projected called realized |

## Hands-on Lab 1 — Offline deterministic acceptance gate
Create `labs/chapter-100/finops_gate.py`:

```python
from dataclasses import dataclass
@dataclass(frozen=True)
class Candidate:
    savings_cents:int
    p99_cpu:float
    failover_headroom:float
    slo_burn:float
    backup_ok:bool
    restore_ok:bool
    rollback_ok:bool
    finance_ok:bool
    sre_ok:bool
    dbre_ok:bool

def reconcile(rows, invoice_cents):
    ids=[r["id"] for r in rows]
    if len(ids)!=len(set(ids)) or any(r["cents"]<0 or not r["owner"] for r in rows):
        raise ValueError("invalid ledger")
    return sum(r["cents"] for r in rows)==invoice_cents

def gate(c):
    checks={"savings":c.savings_cents>0,"peak":c.p99_cpu<=70,
            "failover":c.failover_headroom>=30,"slo":c.slo_burn<=1,
            "backup":c.backup_ok,"restore":c.restore_ok,
            "rollback":c.rollback_ok,"finance":c.finance_ok,
            "sre":c.sre_ok,"dbre":c.dbre_ok}
    return {"decision":"STAGING_ONLY" if all(checks.values()) else "BLOCK",
            "failed":[k for k,v in checks.items() if not v]}
```

The gate returns **STAGING_ONLY**, never authorization to deploy to production. A single missing approval or safety signal blocks the candidate.

## Hands-on Lab 2 — Automated negative tests
Create `labs/chapter-100/test_finops_gate.py`:

```python
import unittest
from dataclasses import replace
from finops_gate import Candidate,reconcile,gate
class GateTests(unittest.TestCase):
    def setUp(self):
        self.safe=Candidate(20000,60,40,0.5,True,True,True,True,True,True)
    def test_reconcile(self):
        self.assertTrue(reconcile([{"id":"a","owner":"team","cents":100}],100))
    def test_mismatch(self):
        self.assertFalse(reconcile([{"id":"a","owner":"team","cents":100}],200))
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            reconcile([{"id":"a","owner":"x","cents":1},{"id":"a","owner":"y","cents":2}],3)
    def test_safe(self):
        self.assertEqual(gate(self.safe)["decision"],"STAGING_ONLY")
    def test_all_controls_fail_closed(self):
        cases={"savings":0,"p99_cpu":90,"failover_headroom":5,"slo_burn":2,
               "backup_ok":False,"restore_ok":False,"rollback_ok":False,
               "finance_ok":False,"sre_ok":False,"dbre_ok":False}
        for field,value in cases.items():
            with self.subTest(field=field):
                self.assertEqual(gate(replace(self.safe,**{field:value}))["decision"],"BLOCK")
if __name__=="__main__":
    unittest.main()
```

Run from the repository root:

```bash
python -m unittest discover -s infrastructure-as-code/labs/chapter-100 -p 'test_*.py' -v
```

## Hands-on Lab 3 — Native cloud financial evidence (manual)
1. Export 30+ days of AWS, Azure and GCP billing data into a restricted staging analytics account.
2. Record billing scope, effective versus amortized cost, taxes, credits, discounts, source checksums and invoice status.
3. Reconcile invoice totals to integer-cent allocations for each tenant and shared Kubernetes platform.
4. Backtest forecast on held-out weeks; measure absolute error and systematic bias.
5. Trigger a synthetic anomaly; verify routing, acknowledgement, owner and audit.
6. Compare AWS Savings Plans/RI, Azure Reservations/Savings Plans and GCP CUD terms against eligible baseline and downside scenarios. **Do not purchase during the lab.**

## Hands-on Lab 4 — Kubernetes and DBRE change rehearsal
1. Capture `kubectl top nodes`, `kubectl get hpa,pdb -A`, scheduling events, resource requests and topology spread.
2. Run load tests for peak demand and a node/zone loss; document p99, error budget, headroom and evictions.
3. Collect database replica lag, checkpoint/IOPS, WAL/oplog, backup age and restore proof.
4. Produce Terraform/OpenTofu `plan` in staging and review replacement, destruction, drift and state locking.
5. Canary an authorized staging change; roll back immediately on latency, error, replication or recovery regression.
6. Obtain separate Finance, SRE, DBRE and change-owner sign-off before considering production.
7. Measure **realized** savings only from a comparable post-change billing cycle; do not equate projected savings with invoice savings.

## Production incident scenarios
| Scenario | Triage | Recovery |
|---|---|---|
| Billing export delayed | source freshness, row count | freeze forecasts; backfill |
| Duplicate cost lines | IDs and hashes | deduplicate and reconcile |
| Shared-node chargeback dispute | allocation weights | quarantine settlement |
| Savings double-counted | credits and commitment basis | rebuild cost baseline |
| Forecast false positives | seasonality and holdout errors | recalibrate |
| Commitment underutilization | eligible coverage | pause new purchases |
| K8s OOM after rightsizing | p99 memory and events | revert limits |
| PDB blocks consolidation | disruption budget | restore nodes |
| PostgreSQL checkpoint latency | IOPS and WAL | revert capacity |
| MongoDB replication lag | secondary lag/elections | restore headroom |
| Redis evictions | memory fragmentation | revert sizing |
| Kafka ISR shrink | broker disk/network | restore capacity |
| Backup lifecycle error | retention and PITR | halt deletion; restore test |
| Canary SLO regression | latency, burn rate | immediate rollback |
| Missing approval | audit/change record | block promotion |
| Unverifiable realized savings | invoices and usage | withhold acceptance |

## Production runbooks
**RB-01 Billing:** freeze settlement, validate lineage and invoice, correct and obtain Finance approval.

**RB-02 Forecast:** stop automated budget decisions, backfill, backtest and document error.

**RB-03 Allocation:** reproduce deterministic cents, resolve ownership, reconcile total.

**RB-04 Commitments:** inspect utilization, eligibility and term; pause purchases pending review.

**RB-05 Kubernetes:** restore requests/nodes, inspect HPA/PDB/events, verify SLO recovery.

**RB-06 DBRE:** halt optimization, restore capacity, inspect replicas and verify restore/RPO/RTO.

**RB-07 IaC rollback:** compare approved baseline, lock state, revert via reviewed plan, verify telemetry.

**RB-08 Audit:** preserve checksums, UTC times, evidence owners, sanitized exports and decision log.

## Final 100-point acceptance assessment
| Control | Points |
|---|---:|
| Billing provenance and invoice tie-out | 15 |
| Shared cost allocation and chargeback | 10 |
| Forecast backtesting and anomalies | 10 |
| Rightsizing and commitment economics | 15 |
| Kubernetes SLO and failover safety | 10 |
| DBRE backup, PITR, restore, RPO/RTO | 15 |
| IaC policy, approval, canary and rollback | 15 |
| Immutable evidence and realized savings | 10 |
| **Total** | **100** |

A score of 90+ is necessary but **not sufficient**. Missing invoice tie-out, restore proof, SLO guardrail, rollback or independent approval is automatic **NO-GO**. Passing synthetic tests proves only the synthetic code paths.

## Deliverables and cleanup
Archive redacted billing lineage, reconciliation, forecast error, candidate rationale, Git/IaC plan, Kubernetes peak/N-1 test, DB restore record, signed approvals, rollback evidence and post-change invoice. Delete only disposable staging resources after verifying ownership and retention. Never delete production backups or cancel commitments as cleanup.

**Next:** Chapter 101 — IaC Disaster Recovery Foundations, RPO/RTO, Backup Architecture and Recovery Design (Part 21).
