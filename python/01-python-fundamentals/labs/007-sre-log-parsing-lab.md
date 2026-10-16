# Chapter 007 — Hands-on Lab: SRE Log Parsing and Error Summary

## Goal
Parse a bounded local log file and produce an aggregate JSON summary by service and HTTP status. The lab never contacts production systems.

## Prerequisites
Python 3.10+ and a writable directory.

## Step 1 — Create `sample.log`
```text
2026-10-16T21:00:00Z level=INFO service=api status=200 latency_ms=34
2026-10-16T21:00:01Z level=ERROR service=api status=503 latency_ms=1200
2026-10-16T21:00:02Z level=ERROR service=worker status=500 latency_ms=850
malformed log record
2026-10-16T21:00:03Z level=INFO service=api status=200 latency_ms=40
```

## Step 2 — Create `log_summary.py`
```python
"""Bounded, read-only parser for a deliberately fixed log schema."""
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import re

LINE_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) "
    r"level=(?P<level>INFO|WARNING|ERROR) "
    r"service=(?P<service>[A-Za-z0-9_-]{1,64}) "
    r"status=(?P<status>\d{3}) latency_ms=(?P<latency>\d{1,9})"
)
MAX_LINE_CHARS = 4096


def parse_line(line: str) -> dict | None:
    if len(line) > MAX_LINE_CHARS:
        return None
    match = LINE_PATTERN.fullmatch(line.rstrip("\r\n"))
    if match is None:
        return None
    parts = match.groupdict()
    try:
        timestamp = datetime.strptime(parts["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    status = int(parts["status"])
    latency = int(parts["latency"])
    if not 100 <= status <= 599:
        return None
    return {
        "timestamp": timestamp.isoformat() + "Z",
        "level": parts["level"],
        "service": parts["service"],
        "status": status,
        "latency_ms": latency,
    }


def summarize(lines) -> dict:
    by_service = Counter()
    by_status = Counter()
    total = malformed = errors = 0
    maximum_latency = 0
    for line in lines:
        total += 1
        event = parse_line(line)
        if event is None:
            malformed += 1
            continue
        by_service[event["service"]] += 1
        by_status[str(event["status"])] += 1
        maximum_latency = max(maximum_latency, event["latency_ms"])
        if event["status"] >= 500:
            errors += 1
    return {
        "total_lines": total,
        "valid_lines": total - malformed,
        "malformed_lines": malformed,
        "http_5xx_events": errors,
        "max_latency_ms": maximum_latency,
        "by_service": dict(sorted(by_service.items())),
        "by_status": dict(sorted(by_status.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only SRE log summary")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        with args.path.open("r", encoding="utf-8") as handle:
            result = summarize(handle)
    except (OSError, UnicodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
    return 1 if result["malformed_lines"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Step 3 — Create `test_log_summary.py`
```python
import unittest
from log_summary import parse_line, summarize, MAX_LINE_CHARS

GOOD = "2026-10-16T21:00:00Z level=ERROR service=api status=503 latency_ms=1200"


class LogSummaryTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(parse_line(GOOD)["status"], 503)

    def test_bad_line(self):
        self.assertIsNone(parse_line("invalid"))

    def test_invalid_date(self):
        self.assertIsNone(parse_line(GOOD.replace("10-16", "13-40")))

    def test_invalid_status(self):
        self.assertIsNone(parse_line(GOOD.replace("status=503", "status=999")))

    def test_long_line(self):
        self.assertIsNone(parse_line("x" * (MAX_LINE_CHARS + 1)))

    def test_missing_field(self):
        self.assertIsNone(parse_line(GOOD.replace(" latency_ms=1200", "")))

    def test_aggregate(self):
        report = summarize([GOOD + "\n", "invalid\n"])
        self.assertEqual(report["total_lines"], 2)
        self.assertEqual(report["malformed_lines"], 1)
        self.assertEqual(report["http_5xx_events"], 1)

    def test_empty(self):
        self.assertEqual(summarize([])["valid_lines"], 0)

    def test_service(self):
        self.assertEqual(parse_line(GOOD)["service"], "api")

    def test_latency(self):
        self.assertEqual(parse_line(GOOD)["latency_ms"], 1200)


if __name__ == "__main__":
    unittest.main()
```

## Step 4 — Execute
```bash
python log_summary.py sample.log
python -m unittest -v test_log_summary.py
python -m py_compile log_summary.py
```

Expected: five lines, four valid, one malformed, two HTTP 5xx events, max latency 1200 ms, and ten passing tests. The CLI exits 1 because the fixture intentionally contains a malformed line.

## Step 5 — Failure injection
1. Change the timestamp to an impossible date; malformed count should increase.
2. Add a line over 4096 characters; parser should reject it.
3. Remove a required field; parser should reject it.
4. Introduce an invalid UTF-8 byte in a separate test file; the CLI should return a readable decoding error.
5. Restore the fixture after each experiment.

## Production considerations
This parser intentionally accepts only a fixed text schema and counts 5xx status codes. It does not infer error rates without a valid denominator, compute latency percentiles, or handle arbitrary structured logs. Never emit raw sensitive log lines into summaries.

## Acceptance checklist
- [ ] JSON summary generated
- [ ] Invalid records counted
- [ ] Ten unit tests pass
- [ ] Oversized lines rejected
- [ ] Error and latency aggregates verified
- [ ] No production systems contacted

## Cleanup
Delete only local lab files when finished.
