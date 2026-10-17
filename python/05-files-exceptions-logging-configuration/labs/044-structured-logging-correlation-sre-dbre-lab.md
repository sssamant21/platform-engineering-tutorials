# Chapter 044 — Structured Logging and Correlation SRE/DBRE Lab

**Python 3.10+ | Standard library | Offline, synthetic, read-only**

Create `observability.py`, `cli.py`, and `test_observability.py` using the complete source below. Create a private `logs/` directory for output.

## 1. observability.py

```python
"""Offline SRE/DBRE structured logging lab."""
import contextvars
import json
import logging
from logging.handlers import RotatingFileHandler
import re
from pathlib import Path

CORRELATION_ID = contextvars.ContextVar("correlation_id", default="unassigned")
EVENTS = {"probe_started", "probe_result", "probe_failed", "incident_opened"}
SERVICES = {"postgresql", "elasticsearch", "kafka", "redis"}
STATUSES = {"healthy", "warning", "critical", "error"}
SECRET = re.compile(r"(?i)(password|token|secret|api[_-]?key)\s*[:=]\s*[^\s,;]+")

def redact(value):
    if not isinstance(value, str):
        return "[REDACTED]"
    return SECRET.sub(lambda m: m.group(1) + "=[REDACTED]", value)[:256]

def valid_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value):
        raise ValueError("invalid correlation ID")
    return value

class JsonFormatter(logging.Formatter):
    def format(self, record):
        event = getattr(record, "event", "probe_failed")
        service = getattr(record, "service", "unknown")
        status = getattr(record, "status", "error")
        if event not in EVENTS or service not in SERVICES or status not in STATUSES:
            raise ValueError("invalid log metadata")
        return json.dumps({
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname, "logger": record.name,
            "event": event, "service": service, "status": status,
            "correlation_id": valid_id(getattr(record, "correlation_id", CORRELATION_ID.get())),
            "message": redact(record.getMessage()),
        }, sort_keys=True, ensure_ascii=False, allow_nan=False)

def configure(path, max_bytes=4096, backups=2):
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 128:
        raise ValueError("invalid max_bytes")
    if isinstance(backups, bool) or not isinstance(backups, int) or not 0 <= backups <= 10:
        raise ValueError("invalid backups")
    path = Path(path)
    if not path.parent.is_dir():
        raise ValueError("log directory must exist")
    logger = logging.getLogger("sre_ch044")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    close(logger)
    handler = RotatingFileHandler(path, maxBytes=max_bytes, backupCount=backups, encoding="utf-8")
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return logger

def emit(logger, event, service, status, message, level=logging.INFO):
    if event not in EVENTS or service not in SERVICES or status not in STATUSES:
        raise ValueError("invalid event metadata")
    if not isinstance(message, str):
        raise ValueError("message must be text")
    logger.log(level, message, extra={"event": event, "service": service, "status": status,
                                     "correlation_id": valid_id(CORRELATION_ID.get())})

def simulate(logger, correlation_id="incident_001"):
    token = CORRELATION_ID.set(valid_id(correlation_id))
    try:
        emit(logger, "probe_started", "postgresql", "healthy", "synthetic preflight started")
        emit(logger, "probe_result", "postgresql", "warning", "replica lag above synthetic warning", logging.WARNING)
        emit(logger, "probe_failed", "elasticsearch", "error", "timeout token=example-secret", logging.ERROR)
    finally:
        CORRELATION_ID.reset(token)

def close(logger):
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
```

## 2. cli.py

```python
import argparse
from pathlib import Path
from observability import configure, simulate, close

def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline JSON logging lab")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--correlation-id", default="incident_001")
    args = parser.parse_args(argv)
    logger = None
    try:
        logger = configure(args.output)
        simulate(logger, args.correlation_id)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    finally:
        if logger is not None:
            close(logger)
    print("Synthetic JSON logs written")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

## 3. test_observability.py — 40 automated tests

```python
import json
import logging
from pathlib import Path
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from observability import CORRELATION_ID, JsonFormatter, configure, emit, redact, valid_id, simulate, close
from cli import main

class LoggingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"app.log"
        self.logger=configure(self.path)
        self.addCleanup(lambda: close(self.logger))
    def records(self):
        for h in self.logger.handlers: h.flush()
        return [json.loads(x) for x in self.path.read_text().splitlines()]
    def test_password(self): self.assertNotIn("hunter2",redact("password=hunter2"))
    def test_token(self): self.assertNotIn("abc",redact("token:abc"))
    def test_secret(self): self.assertNotIn("abc",redact("secret=abc"))
    def test_api_key(self): self.assertNotIn("abc",redact("api_key=abc"))
    def test_nonstring(self): self.assertEqual(redact(4),"[REDACTED]")
    def test_truncation(self): self.assertEqual(len(redact("x"*500)),256)
    def test_id(self): self.assertEqual(valid_id("req_1"),"req_1")
    def test_empty_id(self):
        with self.assertRaises(ValueError): valid_id("")
    def test_space_id(self):
        with self.assertRaises(ValueError): valid_id("bad id")
    def test_long_id(self):
        with self.assertRaises(ValueError): valid_id("x"*65)
    def test_type_id(self):
        with self.assertRaises(ValueError): valid_id(4)
    def test_name(self): self.assertEqual(self.logger.name,"sre_ch044")
    def test_propagate(self): self.assertFalse(self.logger.propagate)
    def test_handler(self): self.assertEqual(type(self.logger.handlers[0]).__name__,"RotatingFileHandler")
    def test_json(self):
        emit(self.logger,"probe_result","postgresql","healthy","ok")
        self.assertEqual(self.records()[0]["message"],"ok")
    def test_level(self):
        emit(self.logger,"probe_failed","kafka","error","bad",logging.ERROR)
        self.assertEqual(self.records()[0]["level"],"ERROR")
    def test_service(self):
        emit(self.logger,"probe_result","redis","healthy","ok")
        self.assertEqual(self.records()[0]["service"],"redis")
    def test_event(self):
        emit(self.logger,"incident_opened","elasticsearch","critical","slow")
        self.assertEqual(self.records()[0]["event"],"incident_opened")
    def test_status(self):
        emit(self.logger,"probe_result","kafka","warning","lag")
        self.assertEqual(self.records()[0]["status"],"warning")
    def test_correlation(self):
        token=CORRELATION_ID.set("req_123")
        try: emit(self.logger,"probe_result","kafka","healthy","ok")
        finally: CORRELATION_ID.reset(token)
        self.assertEqual(self.records()[0]["correlation_id"],"req_123")
    def test_context_reset(self):
        previous=CORRELATION_ID.get()
        simulate(self.logger,"req_5")
        self.assertEqual(CORRELATION_ID.get(),previous)
    def test_simulation_count(self):
        simulate(self.logger)
        self.assertEqual(len(self.records()),3)
    def test_simulation_redaction(self):
        simulate(self.logger)
        self.assertNotIn("example-secret",self.path.read_text())
    def test_bad_event(self):
        with self.assertRaises(ValueError): emit(self.logger,"bad","kafka","healthy","ok")
    def test_bad_service(self):
        with self.assertRaises(ValueError): emit(self.logger,"probe_result","bad","healthy","ok")
    def test_bad_status(self):
        with self.assertRaises(ValueError): emit(self.logger,"probe_result","kafka","bad","ok")
    def test_bad_message(self):
        with self.assertRaises(ValueError): emit(self.logger,"probe_result","kafka","healthy",123)
    def test_bad_maxbytes(self):
        with self.assertRaises(ValueError): configure(self.path,max_bytes=0)
    def test_bad_backups(self):
        with self.assertRaises(ValueError): configure(self.path,backups=-1)
    def test_missing_dir(self):
        with self.assertRaises(ValueError): configure(self.path.parent/"missing"/"a.log")
    def test_no_duplicate_handler(self):
        configure(self.path)
        self.assertEqual(len(self.logger.handlers),1)
    def test_rotation(self):
        configure(self.path,max_bytes=128,backups=2)
        for _ in range(8): emit(self.logger,"probe_result","kafka","healthy","x"*70)
        self.assertTrue((self.path.parent/"app.log.1").exists())
    def test_no_secret(self):
        emit(self.logger,"probe_failed","redis","error","password=topsecret")
        self.assertNotIn("topsecret",self.path.read_text())
    def test_timestamp(self):
        emit(self.logger,"probe_result","redis","healthy","ok")
        self.assertIn("timestamp",self.records()[0])
    def test_logger_field(self):
        emit(self.logger,"probe_result","redis","healthy","ok")
        self.assertEqual(self.records()[0]["logger"],"sre_ch044")
    def test_schema(self):
        emit(self.logger,"probe_result","redis","healthy","ok")
        self.assertEqual(set(self.records()[0]),{"timestamp","level","logger","event","service","status","correlation_id","message"})
    def test_unicode(self):
        emit(self.logger,"probe_result","redis","healthy","café")
        self.assertEqual(self.records()[0]["message"],"café")
    def test_invalid_simulation_id(self):
        with self.assertRaises(ValueError): simulate(self.logger,"bad id")
    def test_cli(self):
        close(self.logger)
        self.assertEqual(main(["--output",str(self.path)]),0)
        self.assertEqual(len(self.path.read_text().splitlines()),3)
    def test_cli_missing_dir(self):
        with self.assertRaises(SystemExit): main(["--output",str(self.path.parent/"no"/"a.log")])

if __name__=="__main__": unittest.main()
```

## 4. Run and validate

```bash
mkdir -p logs
chmod 700 logs
python3 -m unittest -v test_observability.py
python3 -m py_compile observability.py cli.py
python3 cli.py --output logs/synthetic.jsonl --correlation-id incident_001
python3 -c "import json; [json.loads(x) for x in open('logs/synthetic.jsonl', encoding='utf-8')]"
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force logs
py -3 -m unittest -v test_observability.py
py -3 cli.py --output logs/synthetic.jsonl --correlation-id incident_001
```

**Expected:** three JSONL records, warning and error levels, one correlation ID, no literal `example-secret` in the log.

## 5. Failure injection

1. Emit password, token, secret and API key assignments; confirm masking.
2. Emit invalid event/service/status; confirm rejection.
3. Emit an invalid correlation ID; confirm rejection.
4. Force rotation with `max_bytes=128` and confirm `.1` backup.
5. Reconfigure twice; verify only one handler.
6. Verify context ID restoration after simulated execution.
7. Use a nonexistent directory; confirm failure without a false success.
8. Inspect the exact eight-field schema and verify every line parses as JSON.

## 6. Production runbooks

**Duplicate/missing events:** inspect logger levels, propagation, and handler lifecycle.

**Secret leakage:** contain affected logs, rotate exposed credentials and improve allowlisted logging. The demonstration regex does not guarantee complete redaction.

**Disk pressure:** enforce retention, monitor filesystem and ship to central logging.

**Correlation mismatch:** check `ContextVar` set/reset and async propagation.

**Rollback:** pin a known-good schema and formatter; replay sanitized fixtures before rollout.

## 7. Acceptance

- [x] 40 tests executed successfully in a Linux authoring sandbox.
- [x] Rotation, redaction, correlation and JSON schema covered.
- [ ] Re-run on learner's OS and Python version.
- [ ] Review UTC timestamps, sensitive-data controls and multiprocess rotation before real production deployment.

**Safety:** Synthetic logs only; no network or infrastructure operations.
