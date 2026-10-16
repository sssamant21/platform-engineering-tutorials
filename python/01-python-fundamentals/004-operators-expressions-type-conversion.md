# Chapter 004 — Operators, Expressions and Type Conversion

**Part 01 — Python Fundamentals | Python 3.10+ | Level: Beginner**

## Learning objectives
Apply arithmetic, comparison, logical, membership, identity, bitwise and assignment operators; understand precedence and short-circuit evaluation; convert strings to numbers safely; avoid floating-point pitfalls; and implement a read-only SRE capacity calculation.

## 1. Expressions and operators
An expression evaluates to a value. Statements perform actions such as assignment and control flow.

```python
replicas = 3
desired = replicas + 2
print(desired)  # 5
```

### Arithmetic
| Operator | Example | Result |
|---|---|---|
| `+` | `7 + 3` | 10 |
| `-` | `7 - 3` | 4 |
| `*` | `7 * 3` | 21 |
| `/` | `7 / 2` | 3.5 |
| `//` | `7 // 2` | 3 |
| `%` | `7 % 2` | 1 |
| `**` | `2 ** 3` | 8 |

Floor division rounds toward negative infinity: `-7 // 2 == -4`. Modulo is useful for partitioning, but not a substitute for a cryptographic hash.

### Comparison and logical operators
```python
cpu = 85
memory = 72
print(cpu >= 80 and memory >= 70)  # True
print(cpu > 90 or memory > 90)     # False
print(not (cpu < 80))              # True
```

Comparisons can chain: `0 <= cpu <= 100`. `and` and `or` short-circuit and return an operand, not necessarily a Boolean:
```python
name = "" or "unknown"
print(name)  # unknown
```

### Membership and identity
```python
allowed = {"staging", "prod"}
print("prod" in allowed)
a = [1, 2]
b = [1, 2]
print(a == b)  # True: equal values
print(a is b)  # False: distinct list objects
```
Use `is None` for sentinel checks, not `is` to compare strings or numbers.

### Assignment and bitwise operators
```python
retries = 0
retries += 1
flags = 0b1010
print(flags & 0b0010)  # 2
print(flags | 0b0001)  # 11
```
Bitwise operators (`&`, `|`, `^`, `~`, `<<`, `>>`) act on integer bits. Do not confuse them with logical `and`/`or`.

## 2. Precedence and evaluation
```python
print(2 + 3 * 4)    # 14
print((2 + 3) * 4)  # 20
```
Prefer parentheses where an expression could be misunderstood. Avoid side effects in complex conditions.

## 3. Conversion and validation
```python
replicas = int("4")
load = float("82.5")
print(replicas, load)
```
`int("4.5")` raises `ValueError`. `bool("False")` is True because the string is nonempty. For a CLI, use explicit accepted values:
```python
def parse_bool(raw: str) -> bool:
    normalized = raw.strip().lower()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0"}:
        return False
    raise ValueError("expected true/false, yes/no or 1/0")
```

## 4. Floating-point and exact arithmetic
```python
print(0.1 + 0.2 == 0.3)  # False on typical binary floats
import math
print(math.isclose(0.1 + 0.2, 0.3))
```
For exact decimal financial calculations:
```python
from decimal import Decimal
print(Decimal("0.1") + Decimal("0.2") == Decimal("0.3"))
```
Create `Decimal` from strings, not already-rounded float values. For byte counts use integers whenever possible.

## 5. Real-world SRE examples
### CPU capacity
```python
requested_millicores = 2400
allocatable_millicores = 4000
utilization_pct = requested_millicores / allocatable_millicores * 100
print(f"Requested CPU: {utilization_pct:.1f}%")
```
This is **requested-to-allocatable ratio**, not observed CPU utilization.

### Replicas and headroom
```python
current_replicas = 4
desired_replicas = 6
delta = desired_replicas - current_replicas
print(f"Additional replicas: {max(0, delta)}")
```

## 6. Common failures and recovery
| Symptom | Cause | Action |
|---|---|---|
| `ZeroDivisionError` | Total capacity zero | Reject before division |
| `ValueError` | Invalid numeric string | Validate user input |
| `TypeError` | Mixed incompatible types | Convert explicitly |
| Incorrect threshold | `>` instead of `>=` | Test boundary values |
| Unexpected truthiness | `bool("False")` | Use explicit parser |
| `nan` bypasses comparisons | Non-finite float | Check `math.isfinite` |

## 7. Hands-on project
Complete [Chapter 004 — Resource Headroom Calculator Lab](labs/004-resource-headroom-calculator-lab.md). It validates CPU requests against allocatable capacity, reports headroom, and returns clear exit codes without touching Kubernetes or cloud resources.

## 8. Exercises
1. Explain `//` for negative operands.
2. Show the difference between `and` and `&`.
3. Add a threshold boundary test at exactly 80%.
4. Add a test rejecting `NaN`.
5. Explain why a capacity request ratio is not measured utilization.

## Acceptance criteria
- All examples run on Python 3.10+.
- Input validation rejects zero, negative, and non-finite capacity.
- Tests cover healthy/warning/critical boundaries.
- No cloud credentials or destructive operations are needed.

**Next:** Chapter 005 — Conditional Statements and Decision Making.
