# Chapter 009 — User Input, Output and Formatting

**Part 01 — Python Fundamentals | Python 3.10+ | 75–100 minutes**

## Learning objectives
Build safe command-line tools using `input()`, `print()`, `argparse`, `sys.stdin`, `sys.stdout`, `sys.stderr`, formatted strings, JSON, CSV and exit codes. Validate inputs, separate data output from diagnostics, and test CLI behavior.

## 1. Interactive input
```python
environment = input("Environment (dev/staging/prod): ").strip().lower()
if environment not in {"dev", "staging", "prod"}:
    raise ValueError("unsupported environment")
print(f"Selected: {environment}")
```
`input()` returns a string and raises `EOFError` when input is unavailable. Avoid interactive prompts in unattended CI jobs. Never use `eval()` on user input. Avoid prompting for secrets in plain text; use approved secret-management tools.

## 2. Output and formatting
```python
service, latency = "api", 123.456
print(f"{service:<16} {latency:>10.1f} ms")
print("literal", "columns", sep=" | ", end="\n")
```
F-strings support alignment, precision and interpolation. Format numbers for display, but preserve their original precision in machine-readable data.

## 3. Command-line arguments with argparse
```python
import argparse
parser = argparse.ArgumentParser(description="Read-only health summary")
parser.add_argument("--environment", choices=("dev", "staging", "prod"), required=True)
parser.add_argument("--limit", type=int, default=10)
args = parser.parse_args()
if args.limit <= 0:
    parser.error("--limit must be positive")
print(args.environment, args.limit)
```
Use `argparse` for help, defaults, choices and validation. Do not treat CLI arguments as shell code.

## 4. Standard streams and exit codes
```python
import sys
print("INFO: starting", file=sys.stderr)
print('{"status":"healthy"}', file=sys.stdout)
raise SystemExit(0)
```
Keep machine-readable JSON on stdout and human-readable diagnostics on stderr. Common conventions: 0 success, nonzero errors; define and document any alert-specific codes. Note that `argparse` uses exit 2 for usage errors, so do not reuse 2 for a different meaning without a reliable output contract.

## 5. JSON input and output
```python
import json
payload = '{"service":"api","latency_ms":120}'
data = json.loads(payload)
print(json.dumps(data, sort_keys=True, indent=2, allow_nan=False))
```
JSON is suitable for automation. Reject non-finite numbers and validate schema and types after parsing. `bool` is a subclass of `int` in Python: reject it explicitly when a numeric field should not accept it.

## 6. CSV input and output
```python
import csv
import io
source = io.StringIO("service,latency_ms\napi,120\nworker,450\n")
for row in csv.DictReader(source):
    print(row["service"], int(row["latency_ms"]))
```
CSV has no native type system. Validate each field. For spreadsheet-bound exports, beware of formula injection when a cell begins with `=`, `+`, `-` or `@`; choose a documented neutralization strategy if spreadsheet opening is in scope.

## 7. File encodings and newlines
```python
from pathlib import Path
path = Path("report.json")
path.write_text('{"status":"healthy"}\n', encoding="utf-8")
print(path.read_text(encoding="utf-8"))
```
Specify UTF-8. When writing CSV files use `open(..., newline="", encoding="utf-8")`. Avoid overwriting production files without an approved change and backup plan.

## 8. Validation and failure handling
```python
import math
def percent(raw: str) -> float:
    value = float(raw)
    if not math.isfinite(value) or not 0 <= value <= 100:
        raise ValueError("percentage must be finite and in [0, 100]")
    return value
```
Differentiate missing, malformed and out-of-range values. Do not silently substitute zero for missing telemetry. Report errors without echoing secrets or sensitive input.

## 9. SRE/DevOps example: reporting contract
An operational CLI should define inputs, outputs, exit statuses, ordering, failure semantics and a stable JSON schema. It should be read-only by default, deterministic on the same input, and testable without cloud credentials.

## 10. Troubleshooting
| Symptom | Cause | Resolution |
|---|---|---|
| `EOFError` | No interactive stdin | Use CLI flags |
| `ValueError` | Invalid number | Validate and show help |
| `UnicodeDecodeError` | Wrong encoding | Use known UTF-8 source |
| `JSONDecodeError` | Invalid JSON | Validate input format |
| Broken downstream parser | Logs mixed into stdout | Send diagnostics to stderr |
| Incorrect CSV fields | Embedded commas/newlines | Use `csv` module |
| Misleading exit code | Collision with parser errors | Document separate error contract |

## 11. Lab
Complete [Chapter 009 — SRE CLI Report Generator Lab](labs/009-sre-cli-report-generator-lab.md). It reads local JSON telemetry and emits JSON, CSV or text summaries with validation and tests.

## 12. Exercises
1. Add `--environment` filtering with tests.
2. Explain why machine-readable stdout must be clean.
3. Add malformed JSON and missing file failure tests.
4. Explain how `input()` differs from `argparse`.
5. Document your CLI exit-code contract.

**Next:** Chapter 010 — Python Fundamentals Hands-On Project: System Health Checker.
