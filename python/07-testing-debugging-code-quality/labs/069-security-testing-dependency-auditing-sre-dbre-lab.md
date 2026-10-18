# Chapter 069 — Security Testing and Dependency Auditing SRE/DBRE Lab

**Python 3.11+ | Offline synthetic PostgreSQL, Elasticsearch and Kafka telemetry | No live services**

## 1. Architecture and files
\`\`\`text
ch069/
  secure_ops.py
  test_secure_ops.py
  requirements-security.txt
\`\`\`
Threats: untrusted ticket/telemetry fields, shell injection, leaked subprocess output, compromised dependencies and CI secrets. This lab runs only Python's interpreter with a fixed synthetic command.

## 2. Complete application — secure_ops.py
\`\`\`python
from __future__ import annotations
from dataclasses import dataclass
import json
import math
import re
import subprocess
import sys
from typing import Callable

class SecurityError(ValueError): pass
class CommandError(RuntimeError): pass

POLICY = {
    "postgresql": ("replication_lag", "seconds", 30, 120),
    "elasticsearch": ("search_latency", "milliseconds", 200, 500),
    "kafka": ("consumer_lag", "messages", 1000, 10000),
}
IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")

@dataclass(frozen=True)
class Reading:
    engine: str
    service: str
    value: float

def validate(raw: object) -> Reading:
    if not isinstance(raw, dict) or set(raw) != {"engine","service","metric","unit","value"}:
        raise SecurityError("invalid schema")
    engine, service = raw["engine"], raw["service"]
    if not isinstance(engine, str) or engine not in POLICY:
        raise SecurityError("invalid engine")
    if not isinstance(service, str) or IDENTIFIER.fullmatch(service) is None:
        raise SecurityError("invalid service")
    metric, unit, _, _ = POLICY[engine]
    if raw["metric"] != metric or raw["unit"] != unit:
        raise SecurityError("invalid metric or unit")
    value = raw["value"]
    if type(value) not in (int,float):
        raise SecurityError("invalid numeric type")
    try:
        number = float(value)
    except (ValueError, OverflowError) as exc:
        raise SecurityError("invalid numeric value") from exc
    if not math.isfinite(number) or number < 0:
        raise SecurityError("invalid numeric value")
    return Reading(engine,service,number)

def severity(reading: Reading) -> str:
    _, _, warning, critical = POLICY[reading.engine]
    return "critical" if reading.value >= critical else "warning" if reading.value >= warning else "healthy"

def analyze(rows: object) -> dict[str, object]:
    if not isinstance(rows,list) or len(rows)>100:
        raise SecurityError("invalid batch")
    parsed = [validate(row) for row in rows]
    if len({(row.engine,row.service) for row in parsed}) != len(parsed):
        raise SecurityError("duplicate source")
    counts = {"healthy":0,"warning":0,"critical":0}
    for row in parsed:
        counts[severity(row)] += 1
    return {"dry_run":True,"total":len(parsed),"counts":counts}

def run_diagnostic(
    command: str, *,
    timeout: float = 2.0,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> str:
    # Fixed executable and fixed argument list. Never accept arbitrary shell fragments.
    if command not in ("version","demo"):
        raise SecurityError("command not allowlisted")
    if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0 < timeout <= 10:
        raise SecurityError("invalid timeout")
    args = [sys.executable, "--version"] if command == "version" else [
        sys.executable, "-c", "print('synthetic-ok')"]
    try:
        completed = runner(args, shell=False, check=True, capture_output=True,
                           text=True, timeout=timeout)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        # Do not surface raw stderr, stdout, command output or exception details.
        raise CommandError("sanitized subprocess failure") from None
    if not isinstance(completed.stdout,str) or len(completed.stdout)>4096:
        raise CommandError("invalid output")
    return completed.stdout.strip()

def fixtures() -> list[dict[str, object]]:
    return [
        {"engine":"postgresql","service":"pg-replica","metric":"replication_lag","unit":"seconds","value":45},
        {"engine":"elasticsearch","service":"es-search","metric":"search_latency","unit":"milliseconds","value":650},
        {"engine":"kafka","service":"kafka-worker","metric":"consumer_lag","unit":"messages","value":10000},
    ]

if __name__ == "__main__":
    print(json.dumps(analyze(fixtures()),sort_keys=True))
\`\`\`

## 3. Complete tests — test_secure_ops.py
\`\`\`python
import json
import math
import subprocess
import sys
import unittest
from unittest.mock import Mock
from secure_ops import (
    CommandError, SecurityError, analyze, fixtures, run_diagnostic, severity, validate
)
PG={"engine":"postgresql","service":"pg-replica","metric":"replication_lag","unit":"seconds","value":45}

class SecurityTests(unittest.TestCase):
    def test_summary(self):
        self.assertEqual(analyze(fixtures())["counts"],{"healthy":0,"warning":1,"critical":2})
    def test_empty(self): self.assertEqual(analyze([])["total"],0)
    def test_valid(self): self.assertEqual(validate(PG).value,45)
    def test_schema(self):
        with self.assertRaises(SecurityError): validate({"wrong":1})
    def test_engine(self):
        with self.assertRaises(SecurityError): validate({**PG,"engine":"mysql"})
    def test_metric(self):
        with self.assertRaises(SecurityError): validate({**PG,"metric":"wrong"})
    def test_unit(self):
        with self.assertRaises(SecurityError): validate({**PG,"unit":"ms"})
    def test_identifier_injection(self):
        for bad in ("../etc/passwd","node; rm -rf /","$(id)","node name"):
            with self.subTest(bad=bad):
                with self.assertRaises(SecurityError): validate({**PG,"service":bad})
    def test_bad_values(self):
        for bad in (True,-1,math.nan,math.inf,"45"):
            with self.subTest(bad=bad):
                with self.assertRaises(SecurityError): validate({**PG,"value":bad})
    def test_duplicate(self):
        with self.assertRaises(SecurityError): analyze([PG,PG])
    def test_batch_limit(self):
        with self.assertRaises(SecurityError): analyze([PG]*101)
    def test_threshold(self):
        self.assertEqual(severity(validate({**PG,"value":120})),"critical")
    def test_allowlisted_argv(self):
        runner=Mock(return_value=subprocess.CompletedProcess(["x"],0,"ok\n",""))
        self.assertEqual(run_diagnostic("demo",runner=runner),"ok")
        self.assertEqual(runner.call_args.args[0][0],sys.executable)
        self.assertIs(runner.call_args.kwargs["shell"],False)
        self.assertTrue(runner.call_args.kwargs["check"])
    def test_injection_never_runs(self):
        runner=Mock()
        with self.assertRaises(SecurityError):
            run_diagnostic("demo; rm -rf /",runner=runner)
        runner.assert_not_called()
    def test_bad_timeout(self):
        for bad in (0,-1,11,math.nan,math.inf,True):
            with self.assertRaises(SecurityError):
                run_diagnostic("demo",timeout=bad,runner=Mock())
    def test_timeout_redacted(self):
        runner=Mock(side_effect=subprocess.TimeoutExpired(["secret"],1,output="TOKEN123"))
        with self.assertRaises(CommandError) as cm:
            run_diagnostic("demo",runner=runner)
        self.assertNotIn("TOKEN123",str(cm.exception))
    def test_error_redacted(self):
        runner=Mock(side_effect=subprocess.CalledProcessError(1,["x"],stderr="password=SECRET"))
        with self.assertRaises(CommandError) as cm:
            run_diagnostic("demo",runner=runner)
        self.assertNotIn("SECRET",str(cm.exception))
    def test_large_output(self):
        runner=Mock(return_value=subprocess.CompletedProcess(["x"],0,"x"*4097,""))
        with self.assertRaises(CommandError): run_diagnostic("demo",runner=runner)
    def test_real_offline_command(self):
        self.assertEqual(run_diagnostic("demo"),"synthetic-ok")
    def test_no_secrets(self):
        self.assertNotIn("password",json.dumps(analyze(fixtures())))

if __name__=="__main__": unittest.main()
\`\`\`

## 4. Security tooling
\`\`\`text
# requirements-security.txt
bandit>=1.8,<2
pip-audit>=2.8,<3
\`\`\`
Illustrative ranges, not a locked dependency set. Pin reviewed versions and hashes for enterprise CI.

\`\`\`bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-security.txt
python -m unittest -v test_secure_ops.py
python secure_ops.py
bandit -r secure_ops.py -ll
python -m pip_audit -r requirements-security.txt
\`\`\`
Optional reviewed secrets scan: \`gitleaks git --redact --exit-code 1 .\` on a disposable or approved repository checkout. Validate flags against the pinned scanner version.

## 5. CI quality/security gate (template)
\`\`\`yaml
name: chapter-069-security
on: workflow_dispatch
jobs:
  security:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Verify materialized sources
        run: |
          test -f secure_ops.py
          test -f test_secure_ops.py
          test -f requirements-security.txt
      - name: Install
        run: python -m pip install -r requirements-security.txt
      - name: Unit tests
        run: python -m unittest -v test_secure_ops.py
      - name: SAST
        run: bandit -r secure_ops.py -ll
      - name: Dependency audit
        run: python -m pip_audit -r requirements-security.txt
\`\`\`
Not an active workflow. Extract source blocks, pin reviewed action SHAs, use approved dependency mirrors, add a dedicated secrets-scanning job and enforce branch protection before enabling.

## 6. Incident simulations
1. Inject shell metacharacters into service identifiers.
2. Attempt unallowlisted commands; verify runner never executes.
3. Verify \`shell=False\` and argv lists.
4. Inject subprocess timeout and sanitized error.
5. Inject stderr containing a synthetic token and verify redaction.
6. Simulate missing executable and large stdout.
7. Inject NaN, Infinity, negative and boolean telemetry.
8. Simulate duplicate sources and oversized batches.
9. Add \`shell=True\` in a disposable throwaway file and run Bandit.
10. Test secrets detection with **fake** canary values in a disposable repo.
11. Simulate a critical dependency advisory and document a remediation.
12. Simulate advisory network outage; fail closed rather than mark clean.
13. Inspect least-privilege CI permissions and secret isolation.
14. Restore clean code and rerun all gates.

## 7. Production runbooks
**Critical CVE:** stop promotion, identify affected direct/transitive dependency, patch or obtain time-bound exception, rebuild and retest.

**Credential exposure:** revoke/rotate, restrict artifacts, investigate Git history, assess blast radius and document.

**Injection suspicion:** disable affected automation, remove shell construction, validate argv allowlist, rerun adversarial tests.

**Scanner outage:** block promotion, restore advisory connectivity and rerun.

**Rollback:** restore approved code/lockfile, rerun tests and scans, verify SLOs and record approval.

## 8. 100-point assessment
| Area | Points |
|---|---:|
| Runtime validation and injection prevention | 20 |
| Subprocess controls and error redaction | 20 |
| Bandit SAST | 15 |
| pip-audit SCA and dependency response | 15 |
| Secrets scanning and CI gate safety | 15 |
| Failure drills, runbooks and rollback | 15 |

**Pass:** 90/100 with all mandatory security gates passing and independently verified execution. Publishing this Markdown is not evidence that scans were executed.
