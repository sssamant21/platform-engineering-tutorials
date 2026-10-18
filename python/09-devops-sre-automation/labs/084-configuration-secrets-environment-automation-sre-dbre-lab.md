# Chapter 084 — Configuration, Secrets and Environment Automation SRE/DBRE Lab

**Python 3.11+ | Pydantic v2 | pydantic-settings v2 | PyYAML | TOML | unittest**

## Safety and execution

This lab is local-only. All credentials are synthetic, all URLs use reserved \`.invalid\` domains, and the CLI makes **no network requests**. Extract the following code blocks into a directory called \`ch084\`. No production secret manager is accessed. Tests are supplied but **have not been executed as part of publication**.

\`\`\`text
ch084/
  requirements.txt
  settings.toml
  settings.yaml
  config_lab.py
  test_config_lab.py
\`\`\`

## 1. requirements.txt
\`\`\`text
pydantic>=2.7,<3
pydantic-settings>=2.3,<3
PyYAML>=6.0,<7
\`\`\`
For deployment, pin exact reviewed versions and hashes.

## 2. settings.toml
\`\`\`toml
service_name = "postgres-health"
environment = "lab"
endpoint = "https://db-monitor.example.invalid/health"
timeout_seconds = 3.0
max_retries = 2
tls_verify = true
\`\`\`

## 3. settings.yaml
\`\`\`yaml
service_name: postgres-health
environment: lab
endpoint: https://db-monitor.example.invalid/health
timeout_seconds: 3.0
max_retries: 2
tls_verify: true
\`\`\`

## 4. config_lab.py — complete application
\`\`\`python
"""Validated, redacted configuration with explicit precedence and no network I/O."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tomllib
from typing import Literal, Mapping
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml

MAX_CONFIG_BYTES = 8192
ENV_KEYS = {
    "APP_SERVICE_NAME": "service_name",
    "APP_ENVIRONMENT": "environment",
    "APP_ENDPOINT": "endpoint",
    "APP_TIMEOUT_SECONDS": "timeout_seconds",
    "APP_MAX_RETRIES": "max_retries",
    "APP_TLS_VERIFY": "tls_verify",
}
ALLOWED_KEYS = frozenset(ENV_KEYS.values())
SERVICE_RE = re.compile(r"^[a-z][a-z0-9-]{0,39}$")

class ConfigError(ValueError):
    pass

class Settings(BaseModel):
    """Immutable effective configuration, secrets excluded from config file."""
    model_config = ConfigDict(extra="forbid", frozen=True, strict=False)
    service_name: str = "postgres-health"
    environment: Literal["lab", "staging", "production"] = "lab"
    endpoint: str = "https://db-monitor.example.invalid/health"
    timeout_seconds: float = Field(default=3.0, gt=0, le=30)
    max_retries: int = Field(default=2, ge=0, le=5)
    tls_verify: bool = True

    @field_validator("service_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not SERVICE_RE.fullmatch(value):
            raise ValueError("invalid service name")
        return value

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, value: str) -> str:
        try:
            parts = urlsplit(value)
            port = parts.port  # reject invalid ports
        except ValueError as exc:
            raise ValueError("invalid endpoint URL") from exc
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise ValueError("HTTPS endpoint without embedded credentials required")
        if parts.fragment:
            raise ValueError("URL fragments are forbidden")
        if len(value) > 512:
            raise ValueError("endpoint too long")
        return value

    @model_validator(mode="after")
    def secure_defaults(self):
        if not self.tls_verify:
            raise ValueError("TLS verification must remain enabled")
        return self

class SecretInput(BaseSettings):
    """Optional in-memory synthetic credential for lab; never serialize it."""
    model_config = SettingsConfigDict(env_prefix="CH084_", extra="ignore")
    api_token: SecretStr

def _file_dict(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise ConfigError("configuration file must be a regular non-symlink file")
    if path.stat().st_size > MAX_CONFIG_BYTES:
        raise ConfigError("configuration file too large")
    try:
        data = path.read_bytes()
        if path.suffix.lower() == ".toml":
            parsed = tomllib.loads(data.decode("utf-8"))
        elif path.suffix.lower() in (".yaml", ".yml"):
            parsed = yaml.safe_load(data)
        else:
            raise ConfigError("supported extensions: .toml, .yaml, .yml")
    except (UnicodeError, ValueError, yaml.YAMLError) as exc:
        raise ConfigError("configuration parse failure") from exc
    if not isinstance(parsed, dict) or not set(parsed).issubset(ALLOWED_KEYS):
        raise ConfigError("unexpected keys or non-mapping configuration")
    return parsed

def _env_dict(env: Mapping[str, str]) -> dict:
    # Only explicitly allowlisted variables can affect configuration.
    return {field: env[key] for key, field in ENV_KEYS.items() if key in env}

def load_settings(path: Path | None = None, *,
                  env: Mapping[str, str] | None = None,
                  overrides: Mapping[str, object] | None = None) -> Settings:
    """Defaults < file < environment < CLI overrides."""
    merged: dict = {}
    if path is not None:
        merged.update(_file_dict(path))
    merged.update(_env_dict(os.environ if env is None else env))
    if overrides:
        if not set(overrides).issubset(ALLOWED_KEYS):
            raise ConfigError("unknown override")
        merged.update({key:value for key,value in overrides.items() if value is not None})
    try:
        return Settings.model_validate(merged)
    except ValidationError as exc:
        raise ConfigError("configuration validation failed") from exc

def redacted_snapshot(settings: Settings) -> dict:
    """Contains no token, secret source, or credential."""
    return settings.model_dump(mode="json")

def fingerprint(settings: Settings) -> str:
    payload = json.dumps(redacted_snapshot(settings),sort_keys=True,separators=(",",":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def validate_synthetic_secret(value: str) -> SecretInput:
    """Explicit injection prevents accidentally reading real host secrets in tests."""
    if not isinstance(value,str) or not value.startswith("lab-") or len(value)<8:
        raise ConfigError("lab synthetic token required")
    return SecretInput(api_token=SecretStr(value))

def plan(old: Settings, new: Settings) -> dict:
    previous = redacted_snapshot(old)
    current = redacted_snapshot(new)
    changed = sorted(k for k in current if previous[k] != current[k])
    return {
        "changed_keys": changed,
        "changed": bool(changed),
        "old_fingerprint": fingerprint(old),
        "new_fingerprint": fingerprint(new),
    }

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safe configuration inspection")
    parser.add_argument("--config",type=Path)
    parser.add_argument("--timeout-seconds",type=float)
    parser.add_argument("--max-retries",type=int)
    parser.add_argument("--environment",choices=["lab","staging","production"])
    parser.add_argument("--endpoint")
    args = parser.parse_args(argv)
    overrides = {
        "timeout_seconds":args.timeout_seconds,
        "max_retries":args.max_retries,
        "environment":args.environment,
        "endpoint":args.endpoint,
    }
    try:
        settings = load_settings(args.config,overrides=overrides)
    except (ConfigError,OSError):
        print(json.dumps({"status":"invalid_configuration"}),file=sys.stderr)
        return 2
    print(json.dumps({
        "status":"valid",
        "settings":redacted_snapshot(settings),
        "fingerprint":fingerprint(settings),
    },sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
\`\`\`

**Security boundary:** the CLI intentionally does not read a secret or print a token. \`SecretInput\` demonstrates \`pydantic-settings\` and \`SecretStr\` using an explicitly injected synthetic token; it does not implement a real secret-provider client. File-size and symlink checks are teaching controls, not a complete defense against concurrent filesystem races or malicious YAML resource exhaustion.

## 5. test_config_lab.py — automated tests
\`\`\`python
import json
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from config_lab import (
    ConfigError, Settings, _file_dict, fingerprint, load_settings,
    main, plan, redacted_snapshot, validate_synthetic_secret,
)

BASE = """service_name = "postgres-health"
environment = "lab"
endpoint = "https://db-monitor.example.invalid/health"
timeout_seconds = 3.0
max_retries = 2
tls_verify = true
"""

class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.toml=self.root/"settings.toml"
        self.toml.write_text(BASE,encoding="utf-8")
        self.yaml=self.root/"settings.yaml"
        self.yaml.write_text("""service_name: postgres-health
environment: lab
endpoint: https://db-monitor.example.invalid/health
timeout_seconds: 3.0
max_retries: 2
tls_verify: true
""",encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_toml_load(self):
        self.assertEqual(load_settings(self.toml,env={}).max_retries,2)

    def test_yaml_load(self):
        self.assertEqual(load_settings(self.yaml,env={}).service_name,"postgres-health")

    def test_toml_yaml_equivalence(self):
        self.assertEqual(load_settings(self.toml,env={}),load_settings(self.yaml,env={}))

    def test_default_values(self):
        self.assertEqual(load_settings(env={}).timeout_seconds,3.0)

    def test_environment_overrides_file(self):
        s=load_settings(self.toml,env={"APP_TIMEOUT_SECONDS":"5"})
        self.assertEqual(s.timeout_seconds,5.0)

    def test_cli_overrides_environment(self):
        s=load_settings(self.toml,env={"APP_TIMEOUT_SECONDS":"5"},
                        overrides={"timeout_seconds":6})
        self.assertEqual(s.timeout_seconds,6.0)

    def test_unrelated_environment_ignored(self):
        self.assertEqual(load_settings(env={"AWS_SECRET_ACCESS_KEY":"synthetic"}),Settings())

    def test_invalid_toml(self):
        self.toml.write_text("broken = [")
        with self.assertRaises(ConfigError):
            load_settings(self.toml,env={})

    def test_invalid_yaml_root(self):
        self.yaml.write_text("- item\\n- item2\\n")
        with self.assertRaises(ConfigError):
            load_settings(self.yaml,env={})

    def test_unknown_file_key(self):
        self.toml.write_text(BASE+'password = "not-allowed"\\n')
        with self.assertRaises(ConfigError):
            load_settings(self.toml,env={})

    def test_oversized_file(self):
        self.toml.write_text("x"*9000)
        with self.assertRaises(ConfigError):
            load_settings(self.toml,env={})

    def test_symlink_config_rejected(self):
        link=self.root/"link.toml"
        try:
            link.symlink_to(self.toml)
        except (OSError,NotImplementedError):
            self.skipTest("symlink unsupported")
        with self.assertRaises(ConfigError):
            load_settings(link,env={})

    def test_tls_must_be_verified(self):
        with self.assertRaises(ConfigError):
            load_settings(env={"APP_TLS_VERIFY":"false"})

    def test_https_required(self):
        with self.assertRaises(ConfigError):
            load_settings(env={"APP_ENDPOINT":"http://db.example.invalid"})

    def test_embedded_credentials_forbidden(self):
        with self.assertRaises(ConfigError):
            load_settings(env={"APP_ENDPOINT":"https://user:pass@example.invalid"})

    def test_invalid_timeout(self):
        with self.assertRaises(ConfigError):
            load_settings(env={"APP_TIMEOUT_SECONDS":"0"})

    def test_excessive_retries(self):
        with self.assertRaises(ConfigError):
            load_settings(env={"APP_MAX_RETRIES":"100"})

    def test_invalid_environment(self):
        with self.assertRaises(ConfigError):
            load_settings(env={"APP_ENVIRONMENT":"production-ish"})

    def test_invalid_service_name(self):
        with self.assertRaises(ConfigError):
            load_settings(env={"APP_SERVICE_NAME":"../../escape"})

    def test_unknown_override(self):
        with self.assertRaises(ConfigError):
            load_settings(env={},overrides={"danger":"yes"})

    def test_immutable_settings(self):
        s=load_settings(env={})
        with self.assertRaises(Exception):
            s.timeout_seconds=99

    def test_secret_is_masked(self):
        secret=validate_synthetic_secret("lab-token-123")
        self.assertNotIn("lab-token-123",repr(secret))
        self.assertNotIn("lab-token-123",str(secret))

    def test_invalid_synthetic_secret(self):
        with self.assertRaises(ConfigError):
            validate_synthetic_secret("real-secret")

    def test_fingerprint_stable(self):
        self.assertEqual(fingerprint(load_settings(env={})),
                         fingerprint(load_settings(env={})))

    def test_plan_detects_change(self):
        before=load_settings(env={})
        after=load_settings(env={"APP_TIMEOUT_SECONDS":"4"})
        self.assertEqual(plan(before,after)["changed_keys"],["timeout_seconds"])

    def test_plan_noop(self):
        before=load_settings(env={})
        self.assertFalse(plan(before,before)["changed"])

    def test_cli_valid_redacted(self):
        out=StringIO()
        with redirect_stdout(out):
            status=main(["--config",str(self.toml)])
        self.assertEqual(status,0)
        self.assertEqual(json.loads(out.getvalue())["status"],"valid")

    def test_cli_invalid(self):
        err=StringIO()
        with redirect_stderr(err):
            status=main(["--config",str(self.root/"missing.toml")])
        self.assertEqual(status,2)
        self.assertIn("invalid_configuration",err.getvalue())

    def test_no_secret_in_snapshot(self):
        snapshot=redacted_snapshot(load_settings(env={}))
        self.assertNotIn("api_token",snapshot)

if __name__=="__main__":
    unittest.main()
\`\`\`

## 6. Run the lab

\`\`\`bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m compileall -q config_lab.py test_config_lab.py
python -m unittest -v test_config_lab.py

python config_lab.py --config settings.toml
python config_lab.py --config settings.yaml --timeout-seconds 5
APP_MAX_RETRIES=3 python config_lab.py --config settings.toml
\`\`\`

Windows PowerShell:

\`\`\`powershell
py -3 -m venv .venv
.venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest -v test_config_lab.py
$env:APP_MAX_RETRIES="3"
python config_lab.py --config settings.toml
Remove-Item Env:APP_MAX_RETRIES
\`\`\`

## 7. Incident simulation matrix

| Exercise | Verification | Coverage |
|---|---|---|
| Invalid TOML/YAML | Parser rejects input | Automated |
| Unknown field | Fail closed | Automated |
| Oversized file | Size guard | Automated |
| Symlink config | Path guard | Automated |
| Precedence mismatch | File < env < CLI | Automated |
| Invalid timeout/retries | Pydantic bounds | Automated |
| TLS disabled | Validation failure | Automated |
| HTTP endpoint | HTTPS policy | Automated |
| Embedded URL credentials | Validation failure | Automated |
| Invalid environment | Literal allowlist | Automated |
| Secret printed in repr | SecretStr masking | Automated |
| Drift after override | Fingerprint/diff | Automated |
| Secret provider outage | Cached/recovery policy | Guided |
| Kubernetes Secret rotation | Rollout and identity | Guided |
| Stale ConfigMap | Deployment revision check | Guided |
| CI environment poisoning | Allowlist and audit | Guided |
| Concurrent hot reload | Immutable swap | Guided |
| YAML resource exhaustion | Input limits | Guided |
| Database pool saturation | Config rollback | Guided |
| Production credential exposure | Revoke and rotate | Guided |

## 8. Troubleshooting and runbooks

**Validation failure:** preserve the previous effective config, reject the new version, inspect redacted diagnostics, fix and rerun tests.

**Secret rotation:** confirm identity and access, deploy overlapping credential period, refresh connections, verify health, revoke old secret and record audit evidence.

**Drift:** compare approved version, config fingerprint and source precedence; restore through version control.

**Failed rollout:** stop promotion, revert to last-known-good config, validate secret references and dependency SLOs, then open RCA.

**Credential leak:** revoke exposed credential immediately, restrict artifacts, inspect access and ensure logging redaction.

## 9. CI example (not enabled)

\`\`\`yaml
name: chapter-084-config-validation
on: workflow_dispatch
jobs:
  validate:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m pip install -r requirements.txt
      - run: python -m compileall -q config_lab.py test_config_lab.py
      - run: python -m unittest -v test_config_lab.py
\`\`\`

Extract files to the working directory and pin reviewed action SHAs and dependency hashes before enabling CI.

## 10. 100-point assessment

| Domain | Points |
|---|---:|
| TOML/YAML parsing and precedence | 20 |
| Pydantic validation and secure defaults | 20 |
| Secrets and redacted observability | 20 |
| Environment automation and drift | 15 |
| Automated tests and incident drills | 15 |
| Troubleshooting and operational runbooks | 10 |
| **Total** | **100** |

**Acceptance:** at least 90/100, independently executed tests, reviewed dependency pins and successful local configuration checks. A published Markdown lab is not evidence of execution or production readiness.
