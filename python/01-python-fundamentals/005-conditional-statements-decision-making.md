# Chapter 005 — Conditional Statements and Decision Making

**Part 01 — Python Fundamentals | Python 3.10+ | 60–90 minutes**

## Learning objectives
Use `if`, `elif`, and `else` correctly; understand Boolean expressions, short-circuiting, nested decisions, guard clauses, conditional expressions and `match`; design deterministic SRE alert classification with tested thresholds and missing-data handling.

## 1. How Python chooses a branch
An `if` statement evaluates its condition and runs an indented block only when that condition is truthy. `elif` checks another condition if earlier branches failed; `else` is the fallback.

```python
cpu_pct = 87
if cpu_pct >= 95:
    print("critical")
elif cpu_pct >= 80:
    print("warning")
else:
    print("healthy")
# warning
```

Indent with four spaces, avoid mixing tabs and spaces, and test boundary values. **Branch order matters**: check the most severe threshold first.

## 2. Comparisons and Boolean logic
```python
latency_ms = 1200
error_rate_pct = 2.5
if latency_ms > 1000 or error_rate_pct >= 5:
    print("investigate")
if latency_ms > 1000 and error_rate_pct >= 5:
    print("multiple symptoms")
```

`and` and `or` short-circuit. `and` evaluates the right operand only if the left is truthy; `or` evaluates it only if the left is falsy.

```python
total = 0
if total > 0 and 10 / total > 1:
    print("never reached")
```

Truthiness is not the same as parsing: `bool("False")` is `True`. An absent metric must not be silently interpreted as zero.

## 3. Nested conditions versus guard clauses
Nested logic can become difficult to maintain:
```python
def status_nested(value: float | None) -> str:
    if value is not None:
        if 0 <= value <= 100:
            return "critical" if value >= 90 else "healthy"
        return "invalid"
    return "unknown"
```

Guard clauses simplify the happy path:
```python
import math

def status_guarded(value: float | None) -> str:
    if value is None:
        return "unknown"
    if not math.isfinite(value) or not 0 <= value <= 100:
        return "invalid"
    if value >= 90:
        return "critical"
    if value >= 80:
        return "warning"
    return "healthy"
```

## 4. Conditional expressions
```python
replicas = 2
message = "insufficient" if replicas < 3 else "sufficient"
```
Use for simple expressions, not multi-step incident decision trees.

## 5. Structural pattern matching (Python 3.10+)
```python
def action_for(severity: str) -> str:
    match severity:
        case "critical":
            return "page-on-call"
        case "warning":
            return "create-ticket"
        case "healthy":
            return "none"
        case _:
            return "manual-review"
```
`match` dispatches based on patterns; it does not replace threshold comparison. Avoid routing production actions directly from untrusted labels without authorization.

## 6. SRE alert policy: precedence and unknown states
Example policy (illustrative only):
- Critical if CPU >= 95%, memory >= 95%, or error rate >= 10%.
- Warning if CPU >= 80%, memory >= 85%, or error rate >= 5%.
- Healthy otherwise.
- Unknown if any required metric is missing, invalid or non-finite. Do **not** treat missing telemetry as healthy.

```python
import math

def classify(cpu: float | None, memory: float | None, errors: float | None) -> str:
    metrics = (cpu, memory, errors)
    if any(v is None for v in metrics):
        return "unknown"
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and 0 <= v <= 100 for v in metrics):
        return "unknown"
    if cpu >= 95 or memory >= 95 or errors >= 10:
        return "critical"
    if cpu >= 80 or memory >= 85 or errors >= 5:
        return "warning"
    return "healthy"
```

For production alerting, use monitoring-system alert rules, evaluation windows, rate-of-change, deduplication, inhibition, ownership, and runbooks. A single sample is not enough to establish an incident.

## 7. Troubleshooting
| Problem | Cause | Resolution |
|---|---|---|
| `IndentationError` | Incorrect whitespace | Four spaces per block |
| Wrong severity | Warning branch before critical | Evaluate critical first |
| Missing metric shows healthy | Defaulted `None` to zero | Return unknown |
| `nan` bypasses thresholds | Non-finite input | Validate `math.isfinite` |
| `bool("False")` is True | Nonempty strings are truthy | Parse explicitly |
| Complex nested branches | Excessive indentation | Extract functions and use guards |
| `SyntaxError` on `match` | Python < 3.10 | Use supported Python version |

## 8. Hands-on lab
[Chapter 005 — Alert Classification Engine](labs/005-alert-classification-engine-lab.md) builds a read-only CLI with JSON output, deterministic severity rules, explicit unknown states, tests and failure injection.

## 9. Exercises
1. Explain why critical rules run before warning rules.
2. Add an optional latency metric without changing existing semantics.
3. Compare `if/elif` with `match`.
4. Test values exactly at 80%, 85%, 95%, 5% and 10%.
5. Explain how missing telemetry affects alert reliability.

## Acceptance criteria
- Python 3.10+.
- Healthy, warning, critical, and unknown paths covered.
- Boundary and invalid-input tests pass.
- CLI emits machine-readable JSON.
- No external system is modified.

**Next:** Chapter 006 — Loops, Iteration and Control Flow.
