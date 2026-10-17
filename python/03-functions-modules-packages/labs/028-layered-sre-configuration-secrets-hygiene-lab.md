# Chapter 028 — Hands-on Lab: Layered SRE Configuration and Secrets Hygiene

**Python 3.10+ | Standard library only | Offline and read-only**

## Goal
Implement a deterministic configuration loader with safe defaults, JSON file settings, explicit `SRE_` environment overrides and CLI flags. Validate all inputs, redact secret references from output, and simulate a read-only health check.

## 1. Layout
```text
ch028-config/
  config.py
  cli.py
  config.example.json
  test_config.py
```

## 2. `config.example.json`
```json
{
  "environment": "staging",
  "service": "api",
  "timeout_seconds": 8,
  "dry_run": true,
  "secret_ref": "vault://sre/staging/api"
}
```
The `secret_ref` is an inert example identifier, **not a credential**. Do not replace it with real secret contents.

## 3. `config.py`
```python
"""Strict, side-effect-free SRE configuration loader."""
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path

DEFAULTS = {
    "environment": "staging",
    "service": "api",
    "timeout_seconds": 5.0,
    "dry_run": True,
    "secret_ref": "vault://sre/staging/api",
}
ALLOWED = frozenset(DEFAULTS)
ENV_KEYS = {
    "SRE_ENVIRONMENT": "environment",
    "SRE_SERVICE": "service",
    "SRE_TIMEOUT_SECONDS": "timeout_seconds",
    "SRE_DRY_RUN": "dry_run",
    "SRE_SECRET_REF": "secret_ref",
}


@dataclass(frozen=True)
class Config:
    environment: str
    service: str
    timeout_seconds: float
    dry_run: bool
    secret_ref: str

    def safe_summary(self) -> dict:
        return {
            "environment": self.environment,
            "service": self.service,
            "timeout_seconds": self.timeout_seconds,
            "dry_run": self.dry_run,
            "secret_ref": "<redacted>",
        }


def parse_bool(value):
    if isinstance(value, bool):
        return value
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError("dry_run must be true or false")


def validate(data):
    if not isinstance(data, dict) or set(data) != ALLOWED:
        raise ValueError("configuration has missing or unknown keys")
    env, service, secret = data["environment"], data["service"], data["secret_ref"]
    if env not in {"dev", "staging", "prod"} or not isinstance(env, str):
        raise ValueError("environment must be dev, staging or prod")
    if not isinstance(service, str) or not service.strip() or len(service) > 64:
        raise ValueError("service must be a nonempty string of at most 64 characters")
    if not isinstance(secret, str) or not secret.startswith("vault://") or len(secret) < 9:
        raise ValueError("secret_ref must be a nonempty vault reference")
    timeout = data["timeout_seconds"]
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float, str)):
        raise ValueError("timeout_seconds must be numeric")
    try:
        timeout = float(timeout)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("timeout_seconds must be numeric") from exc
    if not math.isfinite(timeout) or not 0 < timeout <= 60:
        raise ValueError("timeout_seconds must be finite and in (0, 60]")
    dry_run = parse_bool(data["dry_run"])
    if env == "prod" and not dry_run:
        raise ValueError("production requires dry_run=true in this lab")
    return Config(env, service, timeout, dry_run, secret)


def load_config(*, file_path=None, environ=None, cli_overrides=None):
    """Merge defaults < file < explicit environment < CLI; never read host env implicitly."""
    merged = dict(DEFAULTS)
    if file_path is not None:
        try:
            raw = Path(file_path).read_text(encoding="utf-8")
            from_file = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid JSON number")))
        except (OSError, UnicodeError, ValueError) as exc:
            raise ValueError("configuration file could not be read or parsed") from exc
        if not isinstance(from_file, dict) or set(from_file) - ALLOWED:
            raise ValueError("configuration file contains unknown fields")
        merged.update(from_file)
    source = {} if environ is None else environ
    unknown = [key for key in source if key.startswith("SRE_") and key not in ENV_KEYS]
    if unknown:
        raise ValueError("unknown SRE_ environment override")
    for key, field in ENV_KEYS.items():
        if key in source:
            merged[field] = source[key]
    if cli_overrides is not None:
        if not isinstance(cli_overrides, dict) or set(cli_overrides) - ALLOWED:
            raise ValueError("unknown CLI configuration field")
        merged.update({key: value for key, value in cli_overrides.items() if value is not None})
    return validate(merged)
```

## 4. `cli.py`
```python
"""Synthetic read-only SRE CLI with sanitized configuration output."""
import argparse
import json
import os
from config import load_config


def main(argv=None, environ=None):
    parser = argparse.ArgumentParser(description="Offline SRE configuration exercise")
    parser.add_argument("--config", help="reviewed JSON configuration path")
    parser.add_argument("--environment", choices=("dev", "staging", "prod"))
    parser.add_argument("--service")
    parser.add_argument("--timeout-seconds", type=float)
    parser.add_argument("--dry-run", choices=("true", "false"))
    parser.add_argument("--show-config", action="store_true")
    args = parser.parse_args(argv)
    overrides = {
        "environment": args.environment,
        "service": args.service,
        "timeout_seconds": args.timeout_seconds,
        "dry_run": args.dry_run,
    }
    try:
        cfg = load_config(
            file_path=args.config,
            environ=os.environ if environ is None else environ,
            cli_overrides=overrides,
        )
    except (TypeError, ValueError) as exc:
        # Never echo input values or exception causes: keep messages fixed/sanitized.
        parser.error(str(exc))
    result = {"configuration": cfg.safe_summary()}
    if not args.show_config:
        result["probe"] = {
            "mode": "synthetic-read-only",
            "service": cfg.service,
            "status": "healthy",
        }
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Important:** The CLI deliberately does not accept a secret value or secret reference override as a flag. The secret reference may come from the reviewed file or allowlisted environment variable; it is never displayed.

## 5. `test_config.py`
```python
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from config import Config, DEFAULTS, load_config, parse_bool, validate
from cli import main


class ConfigTests(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(load_config().environment, "staging")
    def test_default_dry_run(self):
        self.assertTrue(load_config().dry_run)
    def test_frozen(self):
        from dataclasses import FrozenInstanceError
        with self.assertRaises(FrozenInstanceError):
            load_config().service = "changed"
    def test_bool_true(self):
        self.assertTrue(parse_bool("true"))
    def test_bool_false(self):
        self.assertFalse(parse_bool("false"))
    def test_bool_invalid(self):
        with self.assertRaises(ValueError):
            parse_bool("yes")
    def test_bool_empty(self):
        with self.assertRaises(ValueError):
            parse_bool("")
    def test_file_override(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            path.write_text(json.dumps({"timeout_seconds": 9}), encoding="utf-8")
            self.assertEqual(load_config(file_path=path).timeout_seconds, 9)
    def test_environment_override(self):
        self.assertEqual(load_config(environ={"SRE_SERVICE": "db"}).service, "db")
    def test_cli_precedence(self):
        cfg = load_config(environ={"SRE_SERVICE": "db"}, cli_overrides={"service": "api"})
        self.assertEqual(cfg.service, "api")
    def test_unknown_env(self):
        with self.assertRaises(ValueError):
            load_config(environ={"SRE_MISSPELLED": "1"})
    def test_unknown_cli(self):
        with self.assertRaises(ValueError):
            load_config(cli_overrides={"unknown": 1})
    def test_unknown_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            path.write_text('{"unexpected":1}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(file_path=path)
    def test_bad_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            path.write_text("{bad", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(file_path=path)
    def test_missing_file(self):
        with self.assertRaises(ValueError):
            load_config(file_path="nonexistent-ch028.json")
    def test_negative_timeout(self):
        with self.assertRaises(ValueError):
            load_config(cli_overrides={"timeout_seconds": -1})
    def test_nan_timeout(self):
        with self.assertRaises(ValueError):
            load_config(cli_overrides={"timeout_seconds": float("nan")})
    def test_infinite_timeout(self):
        with self.assertRaises(ValueError):
            load_config(cli_overrides={"timeout_seconds": float("inf")})
    def test_boolean_timeout(self):
        with self.assertRaises(ValueError):
            load_config(cli_overrides={"timeout_seconds": True})
    def test_timeout_max(self):
        self.assertEqual(load_config(cli_overrides={"timeout_seconds": 60}).timeout_seconds, 60)
    def test_timeout_above_max(self):
        with self.assertRaises(ValueError):
            load_config(cli_overrides={"timeout_seconds": 61})
    def test_empty_service(self):
        with self.assertRaises(ValueError):
            load_config(cli_overrides={"service": ""})
    def test_empty_secret(self):
        with self.assertRaises(ValueError):
            load_config(environ={"SRE_SECRET_REF": ""})
    def test_bad_secret_scheme(self):
        with self.assertRaises(ValueError):
            load_config(environ={"SRE_SECRET_REF": "plaintext"})
    def test_prod_dry_run(self):
        self.assertEqual(load_config(cli_overrides={"environment": "prod"}).environment, "prod")
    def test_prod_not_dry_run(self):
        with self.assertRaises(ValueError):
            load_config(cli_overrides={"environment": "prod", "dry_run": "false"})
    def test_summary_redaction(self):
        self.assertEqual(load_config().safe_summary()["secret_ref"], "<redacted>")
    def test_cli_output(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["--show-config"], environ={}), 0)
        self.assertNotIn("vault://", output.getvalue())
        self.assertIn("<redacted>", output.getvalue())
    def test_cli_error_exit(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                main(["--timeout-seconds", "-1"], environ={})
        self.assertEqual(raised.exception.code, 2)
    def test_no_defaults_mutation(self):
        load_config(cli_overrides={"service": "db"})
        self.assertEqual(DEFAULTS["service"], "api")


if __name__ == "__main__":
    unittest.main()
```

## 6. Execute
```bash
python cli.py --config config.example.json --show-config
python cli.py --config config.example.json --environment dev --service db
python -m unittest -v test_config.py
python -m py_compile config.py cli.py
```

PowerShell:
```powershell
$env:SRE_SERVICE = "postgres"
python cli.py --config config.example.json --show-config
Remove-Item Env:SRE_SERVICE
python -m unittest -v test_config.py
```

Expected: sanitized JSON with `secret_ref` shown only as `<redacted>`. The synthetic probe returns `healthy`; it does **not** test a real service. The lab includes **30 unit tests**.

## 7. Failure injection
1. `--timeout-seconds -1` — reject invalid range.
2. `--timeout-seconds nan` — reject nonfinite value.
3. `SRE_DRY_RUN=false` with `--environment prod` — reject unsafe combination.
4. `SRE_SECRET_REF=` — reject empty secret reference.
5. Unknown `SRE_` variable — reject unexpected configuration.
6. Malformed JSON — fail without printing the file contents.
7. Override file timeout with environment then CLI — verify precedence.

## 8. Troubleshooting and production controls
| Problem | Explanation | Response |
|---|---|---|
| Config differs between CI and local | Inherited `SRE_` environment variables | Pass explicit environment map in tests |
| Secret reference appears in logs | Raw configuration serialization | Use safe summary only |
| Empty override unexpectedly accepted | Missing strict validation | Reject empty values |
| Production mode enabled | Unsafe default or flag combination | Enforce dry-run policy |
| Tests fail under old Python | Python version below 3.10 | Use Python 3.10+ |

## 9. Acceptance
- [ ] All 30 unit tests pass locally.
- [ ] Precedence: defaults < file < environment < CLI.
- [ ] Unknown fields rejected.
- [ ] NaN, infinity and invalid booleans rejected.
- [ ] Production dry-run policy enforced.
- [ ] Secret references redacted in reports.
- [ ] No real secrets, network calls or infrastructure changes.

**Limitations:** Environment variables are not a secrets vault; this lab does not retrieve, rotate or authenticate secrets. It models configuration policy and sanitized output only.
