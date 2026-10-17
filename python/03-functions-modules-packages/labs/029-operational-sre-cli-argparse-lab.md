# Chapter 029 — Hands-on Lab: Operational SRE CLI with argparse

**Python 3.10+ | Standard library only | Offline/read-only**

## 1. Design
Implement four subcommands:
- `check`: classify one synthetic service latency.
- `batch`: classify a JSON array of synthetic records.
- `plan`: preview a maintenance operation; never execute.
- `version`: print CLI version.

```text
CLI → argparse → validation → pure classifier/planner → JSON stdout + exit code
```

## 2. `srectl.py`
```python
"""Read-only SRE CLI lab: no network calls or mutations."""
import argparse
import json
import math
from pathlib import Path

VERSION = "0.1.0"
SCHEMA_VERSION = 1
TARGETS = ("elasticsearch", "postgresql", "kubernetes", "kafka")


class InputFailure(Exception):
    pass


class SafetyBlocked(Exception):
    pass


def finite_nonnegative(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{field} must be finite and nonnegative")
    return float(value)


def classify(service, latency_ms, warning_ms=200, critical_ms=500):
    if not isinstance(service, str) or not service.strip():
        raise ValueError("service must be nonempty")
    latency = finite_nonnegative(latency_ms, "latency_ms")
    warning = finite_nonnegative(warning_ms, "warning_ms")
    critical = finite_nonnegative(critical_ms, "critical_ms")
    if not 0 < warning < critical:
        raise ValueError("thresholds must satisfy 0 < warning < critical")
    status = "critical" if latency >= critical else "warning" if latency >= warning else "healthy"
    return {"service": service, "latency_ms": latency, "status": status}


def batch_report(records):
    if not isinstance(records, list):
        raise ValueError("expected a JSON array")
    seen = set()
    results = []
    for record in records:
        if not isinstance(record, dict) or set(record) != {"service", "latency_ms"}:
            raise ValueError("invalid record schema")
        result = classify(record["service"], record["latency_ms"])
        if result["service"] in seen:
            raise ValueError("duplicate service")
        seen.add(result["service"])
        results.append(result)
    results.sort(key=lambda item: item["service"])
    return {"schema_version": SCHEMA_VERSION, "services": results,
            "service_count": len(results),
            "breach_count": sum(item["status"] != "healthy" for item in results)}


def plan(environment, target, *, execute=False):
    if environment not in {"dev", "staging", "prod"}:
        raise ValueError("invalid environment")
    if target not in TARGETS:
        raise ValueError("invalid target")
    if execute:
        raise SafetyBlocked("execution is disabled in this read-only lab")
    return {"schema_version": SCHEMA_VERSION, "environment": environment,
            "target": target, "action": "inspect-health", "dry_run": True,
            "mutations": []}


def parser_factory():
    parser = argparse.ArgumentParser(
        prog="srectl", description="Offline operational SRE CLI"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="classify one synthetic service")
    check.add_argument("--service", required=True)
    check.add_argument("--latency-ms", type=float, required=True)
    check.add_argument("--warning-ms", type=float, default=200)
    check.add_argument("--critical-ms", type=float, default=500)
    batch = sub.add_parser("batch", help="classify a JSON file")
    batch.add_argument("--input", type=Path, required=True)
    maintenance = sub.add_parser("plan", help="preview an operation (never executes)")
    maintenance.add_argument("--environment", choices=("dev", "staging", "prod"), required=True)
    maintenance.add_argument("--target", choices=TARGETS, required=True)
    maintenance.add_argument("--execute", action="store_true",
                             help="deliberately blocked; demonstrates safety control")
    sub.add_parser("version", help="print CLI version")
    return parser


def main(argv=None):
    parser = parser_factory()
    args = parser.parse_args(argv)
    try:
        if args.command == "version":
            result = {"version": VERSION, "schema_version": SCHEMA_VERSION}
            exit_code = 0
        elif args.command == "check":
            result = {"schema_version": SCHEMA_VERSION, **classify(
                args.service, args.latency_ms, args.warning_ms, args.critical_ms
            )}
            exit_code = 3 if result["status"] != "healthy" else 0
        elif args.command == "batch":
            try:
                raw = args.input.read_text(encoding="utf-8")
                records = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid JSON number")))
            except (OSError, UnicodeError, ValueError) as exc:
                raise InputFailure("input file could not be read or parsed") from exc
            result = batch_report(records)
            exit_code = 3 if result["breach_count"] else 0
        else:
            result = plan(args.environment, args.target, execute=args.execute)
            exit_code = 0
    except SafetyBlocked as exc:
        parser.exit(4, f"srectl: blocked: {exc}\n")
    except InputFailure as exc:
        parser.exit(5, f"srectl: input failure: {exc}\n")
    except (ValueError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
```

## 3. `metrics.json`
```json
[
  {"service":"api","latency_ms":120},
  {"service":"db","latency_ms":650},
  {"service":"worker","latency_ms":300}
]
```

## 4. `test_srectl.py`
```python
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from srectl import (
    SafetyBlocked, batch_report, classify, finite_nonnegative,
    main, parser_factory, plan,
)


def invoke(args):
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
        try:
            code = main(args)
        except SystemExit as exc:
            code = exc.code
    return code, output.getvalue()


class SreCliTests(unittest.TestCase):
    def test_healthy(self): self.assertEqual(classify("api", 100)["status"], "healthy")
    def test_warning(self): self.assertEqual(classify("api", 200)["status"], "warning")
    def test_critical(self): self.assertEqual(classify("api", 500)["status"], "critical")
    def test_custom_threshold(self): self.assertEqual(classify("api", 80, 50, 100)["status"], "warning")
    def test_negative(self):
        with self.assertRaises(ValueError): classify("api", -1)
    def test_nan(self):
        with self.assertRaises(ValueError): classify("api", float("nan"))
    def test_inf(self):
        with self.assertRaises(ValueError): classify("api", float("inf"))
    def test_bool(self):
        with self.assertRaises(ValueError): finite_nonnegative(True, "latency")
    def test_bad_service(self):
        with self.assertRaises(ValueError): classify("", 10)
    def test_bad_threshold(self):
        with self.assertRaises(ValueError): classify("api", 10, 500, 200)
    def test_empty_batch(self): self.assertEqual(batch_report([])["service_count"], 0)
    def test_batch_sort(self):
        result = batch_report([{"service":"z","latency_ms":1},{"service":"a","latency_ms":1}])
        self.assertEqual(result["services"][0]["service"], "a")
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            batch_report([{"service":"a","latency_ms":1},{"service":"a","latency_ms":2}])
    def test_batch_bad_schema(self):
        with self.assertRaises(ValueError): batch_report([{"service":"api"}])
    def test_batch_nonlist(self):
        with self.assertRaises(ValueError): batch_report({})
    def test_batch_breach(self):
        self.assertEqual(batch_report([{"service":"api","latency_ms":300}])["breach_count"], 1)
    def test_plan_staging(self): self.assertTrue(plan("staging", "postgresql")["dry_run"])
    def test_plan_prod(self): self.assertEqual(plan("prod", "elasticsearch")["mutations"], [])
    def test_plan_invalid_env(self):
        with self.assertRaises(ValueError): plan("unknown", "kafka")
    def test_plan_invalid_target(self):
        with self.assertRaises(ValueError): plan("staging", "unknown")
    def test_plan_execute_blocked(self):
        with self.assertRaises(SafetyBlocked): plan("prod", "kafka", execute=True)
    def test_cli_version(self):
        code, output = invoke(["version"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["version"], "0.1.0")
    def test_cli_check_healthy(self):
        self.assertEqual(invoke(["check","--service","api","--latency-ms","100"])[0], 0)
    def test_cli_check_breach(self):
        self.assertEqual(invoke(["check","--service","api","--latency-ms","300"])[0], 3)
    def test_cli_check_invalid(self):
        self.assertEqual(invoke(["check","--service","api","--latency-ms","nan"])[0], 2)
    def test_cli_plan_blocked(self):
        self.assertEqual(invoke(["plan","--environment","prod","--target","kafka","--execute"])[0], 4)
    def test_cli_missing_input(self):
        self.assertEqual(invoke(["batch","--input","nonexistent-ch029.json"])[0], 5)
    def test_cli_bad_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{bad", encoding="utf-8")
            self.assertEqual(invoke(["batch","--input",str(path)])[0], 5)
    def test_cli_batch_breach(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.json"
            path.write_text(json.dumps([{"service":"api","latency_ms":600}]), encoding="utf-8")
            self.assertEqual(invoke(["batch","--input",str(path)])[0], 3)
    def test_parser_help(self):
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                parser_factory().parse_args(["--help"])
        self.assertEqual(raised.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
```

## 5. Execute
```bash
python srectl.py --help
python srectl.py check --service api --latency-ms 100
python srectl.py check --service api --latency-ms 350
python srectl.py batch --input metrics.json
python srectl.py plan --environment staging --target postgresql
python srectl.py plan --environment prod --target elasticsearch --execute
python -m unittest -v test_srectl.py
python -m py_compile srectl.py
```

**Expected:** healthy check exits 0; warning/critical check and batch breach exit 3; blocked execute exits 4; bad file exits 5. The plan always contains `"dry_run": true` and `"mutations": []`. **30 unit tests** are included. On PowerShell inspect the last exit with `$LASTEXITCODE`; on Bash use `echo $?` immediately after the command.

## 6. Failure injection
1. `--latency-ms nan`: usage failure (2).
2. `batch --input missing.json`: input failure (5).
3. Duplicate service in JSON: validation failure (2).
4. `plan --execute`: policy block (4), no mutation.
5. Malformed JSON: input failure (5).
6. Run warning check in CI: confirm JSON stdout and code 3 are both preserved.

## 7. Troubleshooting
| Symptom | Cause | Action |
|---|---|---|
| CI marks warning as failed job | Exit 3 indicates health breach | Explicitly handle expected health states |
| JSON parser fails | Extra logs in stdout | Keep diagnostics on stderr |
| Unexpected code 2 | Invalid flag or schema | Run `--help` and validate input |
| Attempt to execute blocked | Intentional lab policy | Do not bypass; use approved workflow |
| File errors not actionable | Missing file or malformed JSON | Validate path and file content |

## 8. Acceptance
- [ ] 30 unit tests pass locally.
- [ ] Root and subcommand help available.
- [ ] JSON stdout is deterministic.
- [ ] Exit codes 0, 2, 3, 4 and 5 demonstrated.
- [ ] Dry-run plan cannot mutate infrastructure.
- [ ] No external service access or credentials required.

**Limitations:** This is an offline educational CLI, not an authenticated production administration client. Real-world commands need structured logging, authorization, retries, deadlines and release controls.
