# Chapter 007 — Strings and Text Processing

**Part 01 — Python Fundamentals | Python 3.10+ | Estimated study: 60–90 minutes**

## Learning objectives
Understand immutable Unicode strings; use indexing, slicing, searching, splitting, joining, stripping, formatting and encoding; write bounded regular expressions; and parse structured SRE logs without leaking sensitive information.

## 1. String fundamentals
```python
service = "patient-api"
environment = 'staging'
message = f"service={service} env={environment}"
print(message)
print(len(service), service[0], service[-3:])
```
Strings are immutable: methods return new strings. Indexing and slicing operate on Unicode code points, not necessarily user-perceived grapheme clusters.

## 2. Normalize and inspect text
```python
raw = "  ERROR: disk full  "
clean = raw.strip()
print(clean.lower())
print(clean.startswith("ERROR"))
print(clean.replace("disk", "volume"))
```
Use `casefold()` for Unicode-aware caseless comparison, but do not blindly normalize security-sensitive identifiers. For internationalized text, Unicode normalization may matter:
```python
import unicodedata
normalized = unicodedata.normalize("NFC", "café")
```

## 3. Split, join and partition
```python
line = "status=503 latency_ms=1200"
fields = line.split()
print(fields)
key, sep, value = fields[0].partition("=")
print(key, value)
print(",".join(["node-a", "node-b"]))
```
Prefer `partition("=")` over `split("=")` when values may contain equals signs. For actual CSV, use `csv`; for JSON, use `json`, not string splitting.

## 4. Formatting and representation
```python
latency = 1234.567
print(f"latency_ms={latency:.1f}")
print(repr("line\nnext"))
```
Use `repr()` for debugging control characters. Do not log passwords, bearer tokens, private keys, or personal data.

## 5. Unicode, bytes and encodings
```python
text = "café"
encoded = text.encode("utf-8")
decoded = encoded.decode("utf-8")
assert decoded == text
```
Files and network payloads are bytes; decoding requires an agreed encoding. Prefer explicit `encoding="utf-8"` when reading logs. Handle decoding failures according to a documented policy rather than silently discarding data.

## 6. Regular expressions
```python
import re
pattern = re.compile(r"\bstatus=(\d{3})\b")
match = pattern.search("service=api status=503 latency_ms=1200")
print(match.group(1) if match else None)
```
Use raw strings for patterns. Avoid catastrophic backtracking from nested ambiguous quantifiers on untrusted input. Prefer bounded, simple patterns or structured log formats. Python's built-in `re` has no general-purpose timeout parameter.

## 7. Production log parsing strategy
A robust parser should define the log schema, reject malformed records predictably, validate types and ranges, process input incrementally, cap line length, and avoid echoing raw sensitive lines. Structured JSON logs are preferable when you control the producer.

Example:
```text
2026-10-16T21:00:00Z level=ERROR service=api status=503 latency_ms=1200
```
The accompanying lab parses this exact fixed schema; it is not a generic log parser.

## 8. Security and operational considerations
- Treat logs as untrusted input; cap input sizes and memory use.
- Avoid interpolating log content into shell commands or SQL.
- Mask or omit secrets and regulated data.
- Use timezone-aware timestamps and validate timestamp formats.
- Preserve raw logs securely when incident forensics require them; sanitize output summaries.
- Differentiate malformed records from healthy events.

## 9. Troubleshooting
| Symptom | Cause | Recovery |
|---|---|---|
| `UnicodeDecodeError` | Encoding mismatch | Verify encoding and producer |
| `IndexError` | Missing field after split | Validate field count |
| `ValueError` | Non-numeric metric | Parse with guarded conversion |
| Incorrect regex match | Pattern too permissive | Anchor and test boundaries |
| Excessive memory | Reading huge file at once | Iterate line by line |
| Missing events | Silent skip of invalid lines | Count and report rejects |
| Sensitive values in output | Raw-line echo | Emit aggregates only |

## 10. Lab
Complete [Chapter 007 — SRE Log Parsing and Error Summary Lab](labs/007-sre-log-parsing-lab.md). It uses a local UTF-8 fixture, line-length caps, strict parsing, streaming aggregation, malformed-line counts and unit tests.

## Exercises
1. Add `WARNING` as an accepted log level.
2. Explain `str` versus `bytes`.
3. Test a Unicode service identifier and discuss your policy.
4. Compare regex parsing to `json.loads`.
5. Explain why log line size limits matter.

**Next:** Chapter 008 — Lists, Tuples, Sets and Dictionaries.
