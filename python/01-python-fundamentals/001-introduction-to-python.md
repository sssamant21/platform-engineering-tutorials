# Chapter 001 — Introduction to Python and Real-World Applications

## Learning objectives
Explain what Python is, how the interpreter executes programs, why virtual environments matter, and where Python fits in SRE, DevOps, and platform engineering. Execute a basic Python program and interpret its output.

## 1. What is Python?
Python is a general-purpose, high-level programming language used for automation, web services, data processing, testing, and infrastructure tooling. It emphasizes readable code and has an extensive standard library.

A Python source file (`.py`) is processed by the Python interpreter. CPython commonly compiles source into bytecode and executes that bytecode in its virtual machine; the details vary by Python implementation.

## 2. Python in production engineering
| Domain | Typical use case |
|---|---|
| SRE | Health checks, SLO calculations, incident evidence collection |
| DevOps | CI/CD scripting, deployment validation, release automation |
| Kubernetes | Inspect Pods, Deployments, events and rollout status via APIs |
| Cloud | Inventory and policy checks with AWS, Azure and GCP SDKs |
| Databases | Query diagnostics, maintenance reports and backup verification |
| Observability | Process logs, metrics, traces and alert payloads |

Prefer supported APIs and SDKs over fragile command-output parsing. Use least-privilege credentials and avoid embedding secrets in source code.

## 3. Your first program
Create `hello.py`:

```python
from datetime import datetime, timezone

def main() -> None:
    print("Hello, Python SRE!")
    print(f"UTC time: {datetime.now(timezone.utc).isoformat()}")

if __name__ == "__main__":
    main()
```

Run with `python hello.py` on systems where `python` points to Python 3; on Windows `py -3 hello.py` may be appropriate.

Expected: the greeting and an ISO 8601 UTC timestamp. The timestamp changes on each run.

## 4. Understanding the code
- `from ... import ...` imports library symbols.
- `def main() -> None` declares a function and return annotation.
- `print()` writes text to standard output.
- `if __name__ == "__main__"` runs the entry point only when executed as a script.
- `datetime.now(timezone.utc)` produces a timezone-aware UTC datetime.

## 5. Operational considerations
Python is well suited to automation, but scripts need explicit timeouts, safe retries, structured logs, exception handling, dependency pinning and testing before production use. Avoid running privileged maintenance commands as a learning exercise.

## 6. Troubleshooting
| Symptom | Likely cause | Resolution |
|---|---|---|
| python not found | Interpreter missing or not on PATH | Install Python 3 and reopen terminal |
| SyntaxError | Typo or wrong interpreter | Check source and `python --version` |
| ModuleNotFoundError | Wrong environment or missing package | Check interpreter and active environment |
| IndentationError | Misaligned whitespace | Use consistent four-space indentation |

## 7. Exercises
1. Change the greeting to identify your lab environment.
2. Print the Python interpreter version using `sys.version`.
3. Explain the difference between source code and runtime output.
4. Complete the [hands-on lab](labs/001-introduction-lab.md).

## Acceptance criteria
- Python 3 runs successfully.
- The sample program prints the greeting and timezone-aware UTC timestamp.
- The learner can explain imports, functions, entry points, and execution.
- The lab's system information script passes the supplied checks.

**Next:** Chapter 002 — Python Installation, VS Code, Git and Virtual Environments.
