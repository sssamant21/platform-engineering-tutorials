# Chapter 003 — Python Syntax, Variables and Basic Data Types

**Part 01: Python Fundamentals | Difficulty: Beginner | Estimated lab: 60 minutes**

## Objectives
By the end of this chapter you can write correctly indented Python, use comments and identifiers, distinguish mutable variables from object types, work with int/float/str/bool/None, perform safe conversions, and validate input in an SRE capacity-checking script.

## 1. Python syntax and indentation
Python uses indentation to define blocks, conventionally four spaces. It is case-sensitive. Comments start with `#`; docstrings document modules, classes, and functions.

```python
def classify_cpu(usage: float) -> str:
    """Classify CPU utilization in percent."""
    if usage >= 90:
        return "critical"
    if usage >= 75:
        return "warning"
    return "healthy"

print(classify_cpu(82.5))  # warning
```

Never mix tabs and spaces within a block. Use meaningful `snake_case` names for variables/functions and `UPPER_CASE` for constants by convention.

## 2. Variables, assignment and object identity
Assignment binds a name to an object; it does not declare a fixed storage type. `type(value)` inspects the runtime type, `id(value)` identifies an object within the current process, and `is` checks identity (not value equality).

```python
node_count = 4
node_count = "four"  # allowed, but generally avoid changing meaning/type
print(type(node_count).__name__)  # str

a = [1, 2]
b = a
b.append(3)
assert a == [1, 2, 3]  # same mutable list object
```

Use `==` for value equality; use `is None` for checking the None singleton. Do not depend on object IDs being stable across processes.

## 3. Core types
| Type | Example | Operational application |
|---|---|---|
| `int` | `replicas = 3` | Counts, ports, byte totals |
| `float` | `cpu_pct = 82.5` | Measurements, percentages |
| `str` | `namespace = "staging"` | Names, IDs, log messages |
| `bool` | `healthy = True` | Health flags |
| `NoneType` | `last_error = None` | Missing/unknown values |

Python integers have arbitrary precision, subject to available memory. Binary floating-point cannot represent every decimal fraction exactly; use `decimal.Decimal` for financial quantities when exact decimal arithmetic is required.

```python
replicas: int = 3
cpu_pct: float = 82.5
environment: str = "staging"
healthy: bool = cpu_pct < 90
last_error: str | None = None  # union syntax requires Python 3.10+
print(replicas, cpu_pct, environment, healthy, last_error)
```

Annotations improve tooling and static checks; they do not automatically enforce types at runtime.

## 4. Strings and formatting
```python
service = "patient-api"
namespace = "staging"
print(f"service={service} namespace={namespace}")
print(service.upper())
print(service.startswith("patient"))
```

Strings are immutable. Avoid placing credentials or personal data into logs. Prefer structured logging over interpolated free-form messages in production.

## 5. Operators and comparisons
```python
used_gib = 82
capacity_gib = 100
percent = used_gib / capacity_gib * 100
print(percent >= 80)    # True
print(used_gib // 10)   # 8 (floor division)
print(used_gib % 10)    # 2 (remainder)
```

Use parentheses to clarify operator precedence. Avoid comparing measurements in different units.

## 6. Explicit type conversion
```python
raw_replicas = "5"
replicas = int(raw_replicas)
print(replicas + 1)  # 6
```

`int("five")` raises `ValueError`; `int(None)` raises `TypeError`. `bool("False")` is **True** because any nonempty string is truthy. Parse booleans explicitly instead of casting arbitrary text with `bool()`.

## 7. Input validation and defensive programming
Never trust external command-line input. Reject invalid numbers, non-finite floats (`nan`, `inf`), negative capacities, and percentages outside 0–100. Fail clearly instead of silently substituting values.

```python
import math

def validate_percentage(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 100:
        raise ValueError("percentage must be finite and between 0 and 100")
    return number
```

## 8. SRE use case: capacity warning
```python
def disk_status(used_bytes: int, total_bytes: int) -> str:
    if total_bytes <= 0 or used_bytes < 0 or used_bytes > total_bytes:
        raise ValueError("invalid disk capacity")
    usage_pct = used_bytes / total_bytes * 100
    return "critical" if usage_pct >= 90 else "warning" if usage_pct >= 80 else "healthy"

print(disk_status(85, 100))  # warning
```

This is a demonstration of configurable alert thresholds, not a substitute for filesystem monitoring, trends, or production SLO design.

## 9. Troubleshooting
| Error | Cause | Recovery |
|---|---|---|
| `IndentationError` | Misaligned block | Use four spaces consistently |
| `NameError` | Undefined/misspelled variable | Check name and scope |
| `TypeError` | Incompatible operation | Inspect types, convert deliberately |
| `ValueError` | Invalid numeric text | Validate and report input error |
| `ZeroDivisionError` | Zero denominator | Validate total capacity first |
| Unexpected `bool("False")` | Truthiness, not parsing | Use explicit parser |

## 10. Exercises
1. Change the warning threshold to 75%.
2. Explain why `0.1 + 0.2 == 0.3` may be false.
3. Compare `is` versus `==` with two separate lists.
4. Run the accompanying [Chapter 003 hands-on lab](labs/003-python-types-capacity-check-lab.md).

## Acceptance criteria
- All sample code runs under Python 3.10+.
- Learner identifies types and explains assignment/identity.
- Invalid and non-finite inputs are rejected.
- Lab tests pass and CLI exit codes are checked.

**Next:** Chapter 004 — Operators, Expressions and Type Conversion.
