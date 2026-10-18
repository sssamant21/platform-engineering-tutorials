# Chapter 082 — OS, Process and Service Automation SRE/DevOps/DBRE Lab

**Python 3.11+ | psutil | Standard library | Disposable local workspace**

## Project and safety
\`\`\`text
ch082/
  requirements.txt
  os_service_lab.py
  test_os_service_lab.py
\`\`\`
The lab inspects the local host, writes only to a temporary workspace, and manages only subprocesses it launches. It does not restart real services, kill arbitrary PIDs, delete system files, or require administrator privileges.

### requirements.txt
\`\`\`text
psutil>=5.9,<8
\`\`\`

## Complete application — os_service_lab.py
\`\`\`python
"""Local-only OS, process and service-health automation lab."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

import psutil

class PolicyError(RuntimeError): pass
class ProcessFailure(RuntimeError): pass

@dataclass(frozen=True)
class Health:
    running: bool
    exit_code: int | None
    rss_bytes: int | None

def workspace_file(root: Path, name: str) -> Path:
    if not root.is_dir() or root.is_symlink():
        raise PolicyError("workspace must be existing non-symlink directory")
    if not name or len(name) > 64 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in name):
        raise PolicyError("unsafe filename")
    path = root.resolve() / (name + ".json")
    if path.is_symlink():
        raise PolicyError("symlink destination forbidden")
    return path

def write_marker(root: Path, name: str, state: str, *, apply: bool = False) -> dict:
    if state not in ("healthy","maintenance"):
        raise ValueError("unsupported state")
    path = workspace_file(root,name)
    payload = (json.dumps({"name":name,"state":state},sort_keys=True) + "\\n").encode()
    existing = path.read_bytes() if path.exists() else None
    changed = existing != payload
    if apply and changed:
        fd,tmp = tempfile.mkstemp(prefix=".ch082-",dir=str(root.resolve()))
        try:
            with os.fdopen(fd,"wb") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp,path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        if path.read_bytes() != payload:
            raise ProcessFailure("marker verification failed")
    return {"changed":changed,"applied":bool(apply and changed),
            "sha256":hashlib.sha256(payload).hexdigest()}

def resource_snapshot(path: Path) -> dict:
    disk = shutil.disk_usage(path)
    memory = psutil.virtual_memory()
    return {
        "cpu_percent":float(psutil.cpu_percent(interval=0.05)),
        "memory_total":int(memory.total),
        "memory_available":int(memory.available),
        "disk_total":int(disk.total),
        "disk_free":int(disk.free),
        "pid":os.getpid(),
    }

def start_owned_child(seconds: float = 0.2) -> subprocess.Popen:
    if type(seconds) not in (int,float) or not 0 <= seconds <= 5:
        raise ValueError("invalid sleep duration")
    return subprocess.Popen(
        [sys.executable,"-c","import time; time.sleep(" + repr(seconds) + ")"],
        shell=False,stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
    )

def owned_child_health(child: subprocess.Popen) -> Health:
    code = child.poll()
    if code is not None:
        return Health(False,code,None)
    try:
        rss = int(psutil.Process(child.pid).memory_info().rss)
    except (psutil.NoSuchProcess,psutil.AccessDenied,psutil.ZombieProcess):
        rss = None
    return Health(True,None,rss)

def stop_owned_child(child: subprocess.Popen, *, grace: float = 0.2) -> int:
    """Only accepts an owned Popen handle; no arbitrary PID API."""
    if not isinstance(child,subprocess.Popen):
        raise TypeError("owned subprocess handle required")
    if type(grace) not in (int,float) or not 0 <= grace <= 5:
        raise ValueError("invalid grace")
    if child.poll() is not None:
        return int(child.returncode)
    child.terminate()
    try:
        return int(child.wait(timeout=grace))
    except subprocess.TimeoutExpired:
        child.kill()
        return int(child.wait(timeout=2))

def run_probe(*, timeout: float = 1.0) -> dict:
    if type(timeout) not in (int,float) or not 0 < timeout <= 5:
        raise ValueError("invalid timeout")
    try:
        result = subprocess.run(
            [sys.executable,"-c","print('service-ready')"],
            shell=False,check=True,capture_output=True,text=True,timeout=timeout,
        )
    except (subprocess.TimeoutExpired,subprocess.CalledProcessError,OSError) as exc:
        raise ProcessFailure("probe execution failed") from exc
    return {"ready":result.stdout.strip()=="service-ready","exit_code":result.returncode}

def check_disk(path: Path, *, min_free_bytes: int = 1) -> bool:
    if type(min_free_bytes) is not int or min_free_bytes < 0:
        raise ValueError("invalid free-space threshold")
    return shutil.disk_usage(path).free >= min_free_bytes

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--workspace",type=Path,required=True)
    parser.add_argument("--snapshot",action="store_true")
    parser.add_argument("--probe",action="store_true")
    args=parser.parse_args()
    if not args.workspace.is_dir():
        parser.error("workspace must exist")
    if args.snapshot:
        print(json.dumps(resource_snapshot(args.workspace),sort_keys=True))
    if args.probe:
        print(json.dumps(run_probe(),sort_keys=True))

if __name__=="__main__":
    main()
\`\`\`

## Complete tests — test_os_service_lab.py
\`\`\`python
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch

from os_service_lab import (
    PolicyError,Health,check_disk,owned_child_health,
    resource_snapshot,run_probe,start_owned_child,stop_owned_child,
    workspace_file,write_marker,
)

class OSServiceLabTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.root=Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()

    def test_workspace_file(self):
        self.assertEqual(workspace_file(self.root,"service").name,"service.json")

    def test_path_traversal_rejected(self):
        with self.assertRaises(PolicyError):
            workspace_file(self.root,"../prod")

    def test_empty_name_rejected(self):
        with self.assertRaises(PolicyError):
            workspace_file(self.root,"")

    def test_symlink_target_rejected(self):
        target=self.root/"service.json"
        try:
            target.symlink_to(self.root/"other")
        except (OSError,NotImplementedError):
            self.skipTest("symlinks unsupported")
        with self.assertRaises(PolicyError):
            workspace_file(self.root,"service")

    def test_dry_run_no_mutation(self):
        result=write_marker(self.root,"service","healthy")
        self.assertTrue(result["changed"])
        self.assertFalse((self.root/"service.json").exists())

    def test_apply_writes(self):
        result=write_marker(self.root,"service","healthy",apply=True)
        self.assertTrue(result["applied"])
        self.assertTrue((self.root/"service.json").exists())

    def test_idempotent_repeat(self):
        write_marker(self.root,"service","healthy",apply=True)
        self.assertFalse(write_marker(self.root,"service","healthy",apply=True)["changed"])

    def test_change_state(self):
        write_marker(self.root,"service","healthy",apply=True)
        self.assertTrue(write_marker(self.root,"service","maintenance",apply=True)["changed"])

    def test_invalid_state(self):
        with self.assertRaises(ValueError):
            write_marker(self.root,"service","delete",apply=True)

    def test_snapshot(self):
        result=resource_snapshot(self.root)
        self.assertGreater(result["memory_total"],0)
        self.assertGreaterEqual(result["disk_free"],0)
        self.assertGreaterEqual(result["cpu_percent"],0)

    def test_disk_threshold(self):
        self.assertTrue(check_disk(self.root,min_free_bytes=0))

    def test_disk_threshold_invalid(self):
        with self.assertRaises(ValueError):
            check_disk(self.root,min_free_bytes=-1)

    def test_probe(self):
        self.assertEqual(run_probe()["ready"],True)

    def test_invalid_probe_timeout(self):
        with self.assertRaises(ValueError):
            run_probe(timeout=0)

    def test_child_lifecycle(self):
        child=start_owned_child(1.0)
        try:
            self.assertIsNone(child.poll())
            health=owned_child_health(child)
            self.assertIsInstance(health,Health)
            self.assertTrue(health.running)
        finally:
            stop_owned_child(child)
        self.assertIsNotNone(child.returncode)

    def test_child_natural_exit(self):
        child=start_owned_child(0.01)
        self.assertEqual(child.wait(timeout=2),0)
        self.assertFalse(owned_child_health(child).running)

    def test_repeated_stop(self):
        child=start_owned_child(0.5)
        stop_owned_child(child)
        self.assertEqual(stop_owned_child(child),child.returncode)

    def test_invalid_child_duration(self):
        with self.assertRaises(ValueError):
            start_owned_child(-1)

    def test_invalid_stop_handle(self):
        with self.assertRaises(TypeError):
            stop_owned_child(12345)

    def test_invalid_grace(self):
        child=start_owned_child(0.5)
        try:
            with self.assertRaises(ValueError):
                stop_owned_child(child,grace=-1)
        finally:
            stop_owned_child(child)

if __name__=="__main__":
    unittest.main()
\`\`\`

## Execute locally
\`\`\`bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m compileall -q os_service_lab.py test_os_service_lab.py
python -m unittest -v test_os_service_lab.py
mkdir -p ./ch082-workspace
python os_service_lab.py --workspace ./ch082-workspace --snapshot --probe
\`\`\`
Windows PowerShell: \`py -3 -m venv .venv\`, \`.venv\\Scripts\\Activate.ps1\`, \`New-Item -ItemType Directory -Force ch082-workspace\`, \`py -m unittest -v test_os_service_lab.py\`.

## Incident simulations
1. Path traversal rejection.
2. Symlink target rejection.
3. Dry-run no mutation.
4. Atomic marker write.
5. Idempotent repeat.
6. State drift.
7. Invalid state.
8. CPU resource sample.
9. Memory capacity sample.
10. Disk capacity sample.
11. Disk threshold policy.
12. Child process creation.
13. Child natural exit.
14. Child graceful termination.
15. Repeat stop is safe.
16. Invalid PID handle rejected.
17. Probe readiness check.
18. Probe timeout validation.
19. Disk-full write (guided).
20. Stubborn child requiring kill (guided).
21. Container memory pressure (guided).
22. OS service manager integration (guided).
23. Process privilege failure (guided).
24. Secret leakage in command lines (guided).

Automated tests cover local exercises; OS service manager and production incidents are guided only.

## Troubleshooting and runbooks
**High CPU:** compare sampling intervals and cgroup limits, inspect workload and throttling. **High memory:** compare RSS with host/container limits, inspect OOM events. **Disk pressure:** inspect mount and service ownership, never delete unapproved data. **Hung child:** use retained Popen handle, terminate, wait, kill if necessary, collect exit code. **Readiness:** distinguish process liveness from service and dependency readiness. **Rollback:** restore approved marker/state and verify postconditions.

## CI template
\`\`\`yaml
name: chapter-082-os-process
on: workflow_dispatch
jobs:
  local-tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m pip install -r requirements.txt
      - run: python -m unittest -v test_os_service_lab.py
\`\`\`
Template only. Extract source from Markdown, pin reviewed action SHAs and dependencies, and enable in approved CI.

## 100-point assessment
| Topic | Points |
|---|---:|
| pathlib/os/shutil and path safety | 20 |
| subprocess lifecycle and timeouts | 20 |
| psutil monitoring | 20 |
| Service readiness and health checks | 15 |
| Automated tests and incidents | 15 |
| Runbooks and rollback | 10 |

**Pass:** ≥90/100 with independently executed tests. This lab is not an approved production service-management agent.
