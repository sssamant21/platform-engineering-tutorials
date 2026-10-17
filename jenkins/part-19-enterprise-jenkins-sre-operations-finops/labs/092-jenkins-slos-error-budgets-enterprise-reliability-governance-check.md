# Chapter 092 — Hands-on Lab: Jenkins SLOs, Error Budgets and Reliability Governance

**Environment:** Python 3, optional Prometheus/promtool and Jenkins staging metrics. No production changes.

## 20 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Identify critical Jenkins user journeys | Catalog |
| 02 | Define API availability SLI | Contract |
| 03 | Define queue latency SLI | Contract |
| 04 | Define agent provisioning SLI | Contract |
| 05 | Separate platform from test failures | Matrix |
| 06 | Define 30-day SLO window | Policy |
| 07 | Calculate 99.9% time budget | Math |
| 08 | Calculate 99.95% time budget | Math |
| 09 | Calculate event-based error budget | Output |
| 10 | Calculate 20× burn rate | Output |
| 11 | Implement Python SLO calculator | Script |
| 12 | Run unit tests | Result |
| 13 | Review custom metric labels | Schema |
| 14 | Review PromQL error fraction | Query |
| 15 | Validate multi-window alert design | Review |
| 16 | Simulate high burn | Alert decision |
| 17 | Simulate zero traffic | Edge case |
| 18 | Apply budget governance tabletop | Decision |
| 19 | Review runbooks and escalation | Checklist |
| 20 | Score 100-point acceptance and COA | Sign-off |

## 12 failure drills

1. Zero denominator.
2. Negative eligible event count.
3. Good events exceed total.
4. Invalid SLO target.
5. Missing metrics.
6. Incorrect platform attribution.
7. Queue latency degradation.
8. Counter reset.
9. Low-traffic burn noise.
10. Alert routing missing.
11. Budget exhausted.
12. Emergency security change during freeze.

## Executable offline calculator

Save `slo_calculator.py`:

```python
import argparse
import json

def calculate(good, total, target):
    if type(good) is not int or type(total) is not int or total <= 0 or not 0 <= good <= total:
        raise ValueError("invalid event counts")
    if type(target) not in (int, float) or not 0 < target < 1:
        raise ValueError("invalid target")
    bad = total - good
    allowed = int(total * (1 - target) + 1e-9)
    return {
        "sli": good / total,
        "bad": bad,
        "allowed": allowed,
        "remaining": max(0, allowed - bad),
        "burn": (bad / total) / (1 - target),
        "met": good / total >= target,
    }

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--good", type=int, required=True)
    p.add_argument("--total", type=int, required=True)
    p.add_argument("--target", type=float, default=0.999)
    args = p.parse_args()
    print(json.dumps(calculate(args.good, args.total, args.target), indent=2))
```

```bash
python3 slo_calculator.py --good 99950 --total 100000 --target 0.999
python3 slo_calculator.py --good 98000 --total 100000 --target 0.999
```

Expected first result: 50 bad, 100 allowed, 50 remaining, 0.5× burn. Second: 2,000 bad, 20× burn.

## Automated test

Save `test_slo.py`:

```python
import unittest
from slo_calculator import calculate

class TestSLO(unittest.TestCase):
    def test_healthy(self):
        self.assertEqual(calculate(99950, 100000, 0.999)["remaining"], 50)
    def test_high_burn(self):
        self.assertAlmostEqual(calculate(98000, 100000, 0.999)["burn"], 20.0)
    def test_invalid(self):
        for good, total in ((-1, 100), (101, 100), (0, 0)):
            with self.assertRaises(ValueError):
                calculate(good, total, 0.999)

if __name__ == "__main__":
    unittest.main()
```

```bash
python3 -m unittest -v test_slo.py
```

## Error budget governance tabletop

A T0 Jenkins platform consumes 90% of its monthly budget during repeated agent provisioning failures. A critical security patch is due tonight. Identify decision authority, document risk, protect urgent security work, adjust nonessential releases and establish follow-up reliability work.

## Evidence worksheet

```text
UTC / owner:
SLI definition and attribution:
SLO window and target:
Budget calculations:
Burn rate and alert design:
Python tests:
Governance tabletop:
12 failure drills:
Score / RCA / COA / reviewer:
```

## Acceptance

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or explicitly blocked.
- [ ] SLI eligibility and failure attribution defined.
- [ ] Event/time budgets correctly calculated.
- [ ] High-burn and zero-traffic cases reviewed.
- [ ] Unit tests executed.
- [ ] Multi-window alert design reviewed.
- [ ] Incident and change governance approved.
- [ ] Runbooks and escalation verified.
- [ ] Reviewer sign-off recorded.

**Related:** [Chapter 092 — Jenkins SLOs, Error Budgets and Enterprise Reliability Governance](../092-jenkins-slos-error-budgets-enterprise-reliability-governance.md).
