# Chapter 041 — Files, Paths and Filesystem Operations

**Part 05 — Files, Exceptions, Logging and Configuration | Python 3.10+**

## Outcomes

Use `pathlib.Path`, safe file reading/writing, `os.stat` and permissions, bounded JSON parsing, temporary files, `os.replace`, explicit ownership and exception-safe cleanup to implement a **sandbox-only SRE/DBRE report store**. Understand limitations of atomic replacement and race conditions.

## 1. File and path foundations

`Path` provides platform-aware path composition, existence checks, file metadata and directory iteration.

```python
from pathlib import Path
root = Path("reports")
path = root / "replication.json"
print(path.name, path.suffix, path.parent)
```

Use `Path.resolve()` to normalize a trusted directory, but **do not** assume a resolved path or a string prefix check alone prevents traversal, symlink races or hostile filesystem attacks. The lab accepts only single-component `.json` names and rejects symlinks.

## 2. Read/write safely

Prefer `with` for owned handles, explicit `encoding="utf-8"`, bounded input sizes and validated JSON types. For untrusted JSON, reject non-finite constants using `parse_constant`; Python's default decoder otherwise accepts NaN and Infinity. Validate the report schema after parsing.

```python
with Path("fixture.json").open("r", encoding="utf-8") as handle:
    raw = handle.read()
```

Do not read unbounded files into memory. The lab caps payloads at **1 MiB** and uses binary reading to enforce the byte limit.

## 3. Permissions and least privilege

POSIX permissions distinguish owner, group and others. A new private report should normally use `0600` where supported. The lab creates a temporary file and calls `os.fchmod(fd, 0o600)` on POSIX. On Windows, file permissions are governed by ACLs; do not claim POSIX modes enforce confidentiality there. Restrict access to the parent directory and avoid writing secrets into reports.

## 4. Atomic file replacement

Never overwrite a critical report in place if partial writes are unacceptable.

```text
validate payload -> mkstemp in target directory
 -> write -> flush -> fsync(file)
 -> os.replace(temp, target)
 -> fsync(parent directory on POSIX)
```

`os.replace` gives an atomic name replacement when the underlying filesystem supports it, **not** a distributed transaction, cross-filesystem atomicity, or unconditional crash durability. The directory fsync improves local durability on supported POSIX filesystems. A failure after replacement may mean the new file is already visible; retry policies must account for this.

## 5. Symlinks, traversal and TOCTOU

Reject `../`, absolute paths, subdirectories, backslashes and symlink targets. For reads, `O_NOFOLLOW` where available and `fstat` help reject symlink and non-regular file targets. **Important:** this lab assumes a trusted, private sandbox directory. It is not hardened for a hostile multiuser directory, where attackers can race filesystem entries between checks and replacement. Production designs should use platform-specific dirfd/openat-style operations, ownership checks, appropriate ACLs and security review.

## 6. Exceptions and resource cleanup

Use `try/finally` around temporary files. Do not publish partial reports if JSON serialization, writing or replacement fails. Propagate I/O errors; avoid broad exception handlers that claim success. Do not log raw sensitive payloads.

## 7. SRE/DBRE architecture

```text
synthetic health report -> strict JSON validation
       -> sandbox ReportStore
       -> private temp file + fsync
       -> atomic replace
       -> stable JSON read/list
```

Examples: PostgreSQL backup validation reports, Elasticsearch index-maintenance inventory, Kafka consumer-lag snapshots, Kubernetes preflight evidence. The lab **never deletes data or modifies live services**.

## 8. Troubleshooting

| Symptom | Cause | Action |
|---|---|---|
| Permission denied | ACL/mode or ownership | Inspect parent directory permissions and identity |
| Report partially written | Direct overwrite | Switch to temp + atomic replacement |
| Path traversal attempt | Untrusted filename | Reject any path separators |
| Symlink read | Link to unexpected file | Reject links and use supported no-follow flags |
| Oversized input | No byte limit | Bound reads and serialization |
| NaN in JSON | Permissive default parser | Reject nonfinite constants |
| Temporary files left behind | Missing `finally` | Always unlink on failure |
| Atomic replace fails | Filesystem, ACL or locks | Preserve old file; surface error |
| Durability uncertainty | No fsync or unsupported FS | Validate platform guarantees |
| Unexpected secret exposure | Weak directory ACL | Enforce least privilege and redact output |

## 9. Production runbooks

**Permission incident:** identify effective process identity, inspect file/directory permissions and ACLs, avoid blanket `chmod 777`, repair ownership through approved change.

**Report corruption:** quarantine sanitized artifact, validate source JSON and size, reproduce with fixtures, verify atomic replacement path, restore last known-good report.

**Symlink/path injection:** stop ingestion, inspect directory ownership and unexpected entries, reject path traversal, require security review before resuming.

**Disk full:** stop writes, preserve existing report, inspect filesystem capacity/inodes and cleanup policy; never automatically delete unrelated files.

**Rollback:** pin known-good script, preserve original report, test in a private sandbox, verify new report schema before production adoption.

## 10. Lab and acceptance

[Chapter 041 — Safe Filesystem and Atomic SRE Report Lab](labs/041-safe-filesystem-atomic-sre-report-lab.md) includes complete Python code, CLI, synthetic fixtures, **35 automated unit tests**, failure injection and runbooks. The test suite was executed in a Linux sandbox (35 passed); learners should rerun on their own platform.

**Next: Chapter 042 — File Formats, CSV, JSON and Structured Data Processing.**
