# Chapter 048 — Python Dates, Times, Time Zones and Scheduling Fundamentals

**Part 05 — Files, Exceptions, Logging and Configuration | Python 3.10+ | 5–7 hours**

## Learning objectives

Work safely with aware `datetime` values, UTC timestamps, IANA time zones using `zoneinfo`, daylight-saving gaps and folds, elapsed durations, half-open maintenance windows, deterministic schedule calculations, operational error handling and automated tests.

## 1. Time models for SRE/DBRE

- **Instant:** a unique point on the UTC timeline. Persist aware UTC timestamps.
- **Local civil time:** human wall-clock time in an IANA zone, such as `America/New_York`.
- **Elapsed duration:** calculate by converting instants to UTC before subtraction. Subtracting two datetimes with the same `tzinfo` may use wall-clock arithmetic across DST transitions.
- **Monotonic time:** use `time.monotonic()` for elapsed timeout measurement, not `datetime.now()`.
- **Calendar schedule:** local recurrence rules are different from adding 24 elapsed hours.

```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

instant = datetime(2026, 11, 1, 5, 30, tzinfo=timezone.utc)
local = instant.astimezone(ZoneInfo("America/New_York"))
assert local.fold == 0
```

## 2. Aware versus naive datetimes

A naive datetime does not uniquely identify an instant. Never silently interpret naive timestamps as local server time. Require RFC 3339-like ISO strings with `Z` or a numeric offset. Normalize to UTC before comparing or persisting.

## 3. ZoneInfo and deployment dependencies

`zoneinfo.ZoneInfo` uses system IANA timezone data or the optional `tzdata` package. Windows and minimal containers may need `tzdata` installed. Keep timezone databases current, pin test fixtures and record the time zone explicitly.

## 4. Daylight saving time

**Fall-back fold:** 2026-11-01 01:30 occurs twice in `America/New_York`, once at UTC−04:00 (`fold=0`) and once at UTC−05:00 (`fold=1`). Local timestamps alone cannot distinguish them.

**Spring-forward gap:** 2026-03-08 02:30 does not exist in `America/New_York`. Merely attaching `tzinfo=ZoneInfo(...)` does **not** reject this nonexistent local time. The lab validates by round-tripping both folds through UTC and back. For ambiguous times it requires an explicit `fold` choice.

## 5. Operational time windows

Represent windows as `[start_utc, end_utc)` to avoid double-counting adjacent boundaries. Reject zero/negative durations and impose a maximum duration for the lab. Store the original IANA zone for operator display.

## 6. Schedule calculations

The lab computes the next **daily local wall-clock** occurrence after a supplied UTC instant. On a DST spring gap, it rejects that local time rather than silently shifting it. On a fall fold, operators choose the first or second occurrence explicitly. This example is an educational daily schedule calculator, not a durable scheduler or cron replacement. It does not persist jobs, retry missed runs, enforce leader election or guarantee exactly-once execution.

## 7. Architecture

```text
JSON synthetic maintenance request
  -> strict schema and size checks
  -> aware timestamp and IANA zone validation
  -> local gap/fold resolution
  -> UTC half-open window or next occurrence
  -> deterministic JSON report (no infrastructure mutations)
```

## 8. SRE/DBRE use cases

- PostgreSQL: choose a backup/restore validation window without DST ambiguity.
- Elasticsearch: compare index maintenance times across regions.
- Kafka: avoid consumer-drain scheduling in nonexistent local time.
- Kubernetes: communicate a UTC maintenance window to globally distributed responders.
- Incident analysis: calculate elapsed time from UTC instants rather than local wall-clock subtraction.

## 9. Troubleshooting matrix

| Symptom | Cause | Response |
|---|---|---|
| Off-by-one-hour incident | DST transition | Convert to UTC, verify fold |
| Nonexistent scheduled time | Spring-forward gap | Reject and choose a valid local time |
| Duplicate execution | Fall-back repeated hour | Define first/second fold policy |
| ZoneNotFoundError | Missing IANA tzdata | Install/update system data or `tzdata` |
| Negative elapsed time | Naive or mixed timestamps | Normalize aware instants to UTC |
| Wrong recurrence | Adding 24 hours to UTC | Recalculate local calendar occurrence |
| Missed schedule | Host clock / scheduler restart | Use durable scheduling infrastructure |
| Bad timestamps | Offset absent or malformed | Fail closed with a clear error |

## 10. Production runbooks

**DST-related maintenance failure:** stop further execution, verify original IANA zone, UTC instants, fold policy and audit timestamps. Reschedule through change control.

**Clock skew:** compare host/NTP status and monotonic elapsed measurements; do not rewrite incident timestamps without preserving evidence.

**Timezone-data drift:** identify runtime and tzdata versions, test upcoming transitions in staging, roll out updated data consistently.

**Scheduling rollback:** cancel pending production jobs using the actual scheduler, restore prior schedule definition and verify next run in UTC and local time.

**Incident timeline reconstruction:** collect offset-aware timestamps, normalize to UTC, annotate clock-skew uncertainty and correlate traces/logs.

## 11. Hands-on lab

[Chapter 048 — DST-Safe Maintenance Windows and Scheduling SRE/DBRE Lab](labs/048-dst-safe-maintenance-windows-scheduling-sre-dbre-lab.md) provides complete standard-library Python source, CLI, synthetic fixtures, automated tests, failure injection, runbooks and a 100-point acceptance rubric.

**Next:** Chapter 049 — Python Serialization, Data Validation and Configuration Integration (provisional).
