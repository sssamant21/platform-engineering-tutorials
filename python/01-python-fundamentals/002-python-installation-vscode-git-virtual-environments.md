# Chapter 002 — Python Installation, VS Code, Git and Virtual Environments

**Part 01 — Python Fundamentals | Level: Beginner | Lab: 45–75 minutes**

## Learning objectives
Install and verify a supported Python 3 interpreter; distinguish interpreter, pip, and virtual environments; configure VS Code; initialize Git; create a reproducible local project; diagnose PATH, activation, and dependency problems.

## Architecture
```text
Terminal / VS Code
       |
       v
Project directory -- .venv/ (local, untracked)
       |               |
       |               +-- Python interpreter
       |               +-- pip + installed packages
       |
       +-- src/healthcheck.py
       +-- tests/test_healthcheck.py
       +-- pyproject.toml
       +-- .gitignore
       +-- README.md
```
A virtual environment isolates Python packages for one project. It is not a security boundary, a container, or a replacement for an OS-level dependency manager.

## 1. Install Python
Use an organization-approved supported Python 3 release. For this curriculum, examples target **Python 3.10+**; check package compatibility and security support before choosing a release.

### Windows 11 / PowerShell
Download Python from https://www.python.org/downloads/ or use an approved Windows package manager. During installation, select the launcher and PATH integration when offered. Reopen PowerShell.

```powershell
py -0p
py -3 --version
py -3 -m pip --version
Get-Command py, python -ErrorAction SilentlyContinue
```

The Windows launcher `py` is optional on some installations; if absent, use the installed `python` command. If `python` opens the Microsoft Store, check Windows App Execution Aliases and your PATH configuration.

### Ubuntu / Debian
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
python3 --version
python3 -m pip --version
```
Other Linux distributions have different package names and package managers. Avoid replacing the distribution's system Python.

### macOS
Install Python 3 via an approved package manager or python.org. Verify with `python3 --version`. Do not overwrite Apple's system-managed Python.

## 2. Create an isolated project
```powershell
# PowerShell, from a writable workspace
mkdir python-ch02
cd python-ch02
py -3 -m venv .venv
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip --version
```
PowerShell activation (optional): `.\.venv\Scripts\Activate.ps1`. If execution policy blocks activation, **do not weaken machine-wide policy**; invoke the virtual environment interpreter by its full path.

Linux/macOS:
```bash
mkdir python-ch02 && cd python-ch02
python3 -m venv .venv
./.venv/bin/python --version
./.venv/bin/python -m pip --version
source .venv/bin/activate  # optional
```
Prefer `python -m pip` with the intended interpreter to prevent installing into the wrong environment. Avoid `sudo pip install`.

## 3. VS Code configuration
Install Visual Studio Code and the official Python extension. Open the **project directory** in VS Code. Run **Python: Select Interpreter** from the command palette and choose `.venv`'s Python. In the integrated terminal, verify:
```python
import sys
print(sys.executable)
```
The interpreter path should point to your project's `.venv`. VS Code debugger and terminal can use different interpreters if configured separately; verify both.

## 4. Git and project hygiene
```bash
git --version
git init
```
Create `.gitignore`:
```gitignore
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.env
.vscode/
```
Never commit access tokens, passwords, service-account keys or `.env` files. A virtual environment should be recreated from dependency metadata, not committed.

## 5. Dependencies and reproducibility
For this chapter, the example uses **only Python's standard library**. No third-party dependencies are required. For a real application, document supported Python versions in `pyproject.toml`, use lockfiles or fully resolved constraints appropriate to your dependency manager, scan dependencies, and test upgrades in CI. A `requirements.txt` containing unpinned ranges is not a complete reproducibility guarantee.

Example minimal `pyproject.toml`:
```toml
[project]
name = "python-ch02-healthcheck"
version = "0.1.0"
requires-python = ">=3.10"
description = "Read-only Python environment verification lab"
```

## 6. Interpreter, pip and import diagnostics
```python
import sys
import site
print("Executable:", sys.executable)
print("Version:", sys.version)
print("Site packages:", site.getsitepackages())
```
`sys.executable` identifies the running interpreter. If VS Code and the shell disagree, reselect the interpreter and reopen the terminal.

## 7. Common troubleshooting
| Symptom | Likely cause | Fix |
|---|---|---|
| `py` not recognized | Launcher not installed | Use `python` or install launcher |
| `python` not found | PATH missing | Reopen shell; verify installation |
| `ensurepip` or `venv` missing | Distro package missing | Install `python3-venv` |
| Activation blocked on Windows | PowerShell policy | Run `.venv\Scripts\python.exe` directly |
| Module not found | Wrong interpreter | Inspect `sys.executable`; install with `-m pip` |
| Permission denied | Protected directory | Work in user-owned directory |
| Git author identity missing | Local Git config unset | Set `git config user.name` and `user.email` appropriately |

## 8. Production considerations
- Pin and audit third-party dependencies; keep runtime versions supported.
- Use CI to run tests across supported Python versions.
- Avoid global package installation and privilege escalation.
- Store credentials in approved secret managers, never in source.
- Use least-privilege automation identities.
- Verify package origin and integrity when introducing dependencies.

## 9. Hands-on lab
Complete [Chapter 002 Lab](labs/002-python-development-environment-lab.md) and record command output without secrets.

## Acceptance criteria
1. Interpreter is Python 3.10+.
2. `.venv` exists and `sys.executable` points into it.
3. VS Code selects the project interpreter.
4. Standard-library health check and unit test pass.
5. Git ignores `.venv` and `.env`.

**Next:** Chapter 003 — Python Syntax, Variables and Basic Data Types.
