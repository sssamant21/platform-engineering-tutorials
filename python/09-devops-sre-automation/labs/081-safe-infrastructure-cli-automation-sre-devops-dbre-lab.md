# Chapter 081 — Safe Infrastructure CLI Automation SRE/DevOps/DBRE Lab

**Python 3.11+; standard library only; isolated local workspace**

## Architecture and safety
\`\`\`text
argparse -> validated JSON config -> plan/dry-run -> explicit apply approval
 -> atomic replace of a local state marker -> JSON audit output
 -> bounded, allowlisted subprocess probe -> unittest fault injection
\`\`\`
No production access, cloud credentials or external services are required. Create a disposable workspace and never point the tool at valuable files. This lab intentionally does not implement cross-process locking.

## Project layout
\`\`\`text
ch081/
  config.json
  infra_cli.py
  test_infra_cli.py
\`\`\`

### config.json
\`\`\`json
{"target":"lab-service","desired_state":"healthy","generation":1}
\`\`\`

## Complete application: infra_cli.py
\`\`\`python
"""Local-only, idempotent infrastructure CLI lab."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

class PolicyError(Exception): pass
class TransientError(Exception): pass

def load_config(path):
    if not path.is_file() or path.stat().st_size > 4096:
        raise ValueError("invalid config size or path")
    data = json.loads(path.read_text(encoding="utf-8"))
    if set(data) != {"target","desired_state","generation"}:
        raise ValueError("unexpected keys")
    target = data["target"]
    if not isinstance(target,str) or not 1 <= len(target) <= 40:
        raise ValueError("invalid target")
    if not all(c.isascii() and (c.isalnum() or c in "-_") for c in target):
        raise ValueError("invalid target characters")
    if data["desired_state"] not in ("healthy","maintenance"):
        raise ValueError("invalid state")
    if type(data["generation"]) is not int or not 1 <= data["generation"] <= 1000000:
        raise ValueError("invalid generation")
    return data

def marker_path(workspace, target):
    if not workspace.is_dir() or workspace.is_symlink():
        raise PolicyError("workspace must be existing non-symlink directory")
    if not target or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in target):
        raise PolicyError("invalid target")
    path = workspace.resolve() / (target + ".json")
    if path.is_symlink():
        raise PolicyError("symlink marker rejected")
    return path

def desired_bytes(config):
    return (json.dumps(config,sort_keys=True,separators=(",",":")) + "\n").encode()

def plan(workspace, config):
    path = marker_path(workspace,config["target"])
    payload = desired_bytes(config)
    current = path.read_bytes() if path.exists() else None
    return {"target":config["target"],
            "action":"noop" if current == payload else "update",
            "desired_sha256":hashlib.sha256(payload).hexdigest(),
            "current_sha256":hashlib.sha256(current).hexdigest() if current is not None else None}

def apply(workspace, config, approved=False):
    if not approved:
        raise PolicyError("explicit --apply required")
    result = plan(workspace,config)
    if result["action"] == "noop":
        return {**result,"changed":False}
    path = marker_path(workspace,config["target"])
    fd,tmp = tempfile.mkstemp(prefix=".ch081-",dir=str(workspace.resolve()))
    try:
        with os.fdopen(fd,"wb") as f:
            f.write(desired_bytes(config))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    if path.read_bytes() != desired_bytes(config):
        raise RuntimeError("postcondition mismatch")
    return {**result,"changed":True}

def probe(timeout=2.0):
    if type(timeout) not in (float,int) or not 0 < timeout <= 10:
        raise ValueError("invalid timeout")
    try:
        result = subprocess.run(
            [sys.executable,"-c","print('lab-probe-ok')"],
            shell=False,check=True,capture_output=True,text=True,timeout=timeout)
    except (subprocess.TimeoutExpired,subprocess.CalledProcessError,OSError) as exc:
        raise TransientError("probe failed") from exc
    return result.stdout.strip() == "lab-probe-ok"

def retry_transient(operation, attempts=3, sleep=time.sleep):
    if type(attempts) is not int or not 1 <= attempts <= 5:
        raise ValueError("invalid attempts")
    for index in range(attempts):
        try:
            return operation()
        except TransientError:
            if index + 1 == attempts:
                raise
            sleep(min(0.1,0.01 * 2**index))

def emit(event, **fields):
    print(json.dumps({"time":datetime.now(timezone.utc).isoformat(),
                      "event":event,**fields},sort_keys=True))

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace",type=Path,required=True)
    parser.add_argument("--config",type=Path)
    subs = parser.add_subparsers(dest="command",required=True)
    subs.add_parser("plan")
    apply_cmd = subs.add_parser("apply")
    apply_cmd.add_argument("--apply",action="store_true")
    subs.add_parser("status")
    probe_cmd = subs.add_parser("probe")
    probe_cmd.add_argument("--timeout",type=float,default=2.0)
    args = parser.parse_args(argv)
    try:
        if args.command == "probe":
            emit("probe",ok=probe(args.timeout))
            return 0
        if args.config is None:
            raise ValueError("--config required")
        config = load_config(args.config)
        if args.command == "apply":
            emit("apply",**apply(args.workspace,config,args.apply))
        else:
            emit(args.command,**plan(args.workspace,config))
        return 0
    except (ValueError,OSError):
        emit("invalid_input")
        return 2
    except PolicyError:
        emit("policy_denied")
        return 3
    except TransientError:
        emit("transient_failure")
        return 4
    except Exception:
        emit("operation_failed")
        return 5

if __name__ == "__main__":
    raise SystemExit(main())
\`\`\`

## Automated tests: test_infra_cli.py
\`\`\`python
import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from infra_cli import (
    PolicyError,TransientError,apply,desired_bytes,load_config,
    main,marker_path,plan,probe,retry_transient
)

class TestInfraCLI(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.cfg={"target":"lab-service","desired_state":"healthy","generation":1}
        self.path=self.root/"config.json"
        self.path.write_text(json.dumps(self.cfg))
    def tearDown(self):
        self.temp.cleanup()
    def test_config(self):
        self.assertEqual(load_config(self.path),self.cfg)
    def test_plan_no_mutation(self):
        self.assertEqual(plan(self.root,self.cfg)["action"],"update")
        self.assertFalse((self.root/"lab-service.json").exists())
    def test_apply_requires_approval(self):
        with self.assertRaises(PolicyError):
            apply(self.root,self.cfg)
    def test_apply(self):
        self.assertTrue(apply(self.root,self.cfg,True)["changed"])
        self.assertEqual((self.root/"lab-service.json").read_bytes(),desired_bytes(self.cfg))
    def test_idempotency(self):
        apply(self.root,self.cfg,True)
        self.assertFalse(apply(self.root,self.cfg,True)["changed"])
    def test_generation_drift(self):
        apply(self.root,self.cfg,True)
        updated={**self.cfg,"generation":2}
        self.assertEqual(plan(self.root,updated)["action"],"update")
    def test_path_traversal(self):
        self.cfg["target"]="../prod"
        self.path.write_text(json.dumps(self.cfg))
        with self.assertRaises(ValueError):
            load_config(self.path)
    def test_invalid_state(self):
        self.cfg["desired_state"]="delete"
        self.path.write_text(json.dumps(self.cfg))
        with self.assertRaises(ValueError):
            load_config(self.path)
    def test_invalid_generation(self):
        self.cfg["generation"]=True
        self.path.write_text(json.dumps(self.cfg))
        with self.assertRaises(ValueError):
            load_config(self.path)
    def test_oversized_config(self):
        self.path.write_text("x"*5000)
        with self.assertRaises(ValueError):
            load_config(self.path)
    def test_symlink_marker(self):
        marker=self.root/"lab-service.json"
        try:
            marker.symlink_to(self.path)
        except (OSError,NotImplementedError):
            self.skipTest("symlinks unsupported")
        with self.assertRaises(PolicyError):
            marker_path(self.root,"lab-service")
    def test_probe(self):
        self.assertTrue(probe())
    def test_probe_timeout_validation(self):
        with self.assertRaises(ValueError):
            probe(0)
    def test_retry_success(self):
        calls=[]
        def fn():
            calls.append(1)
            if len(calls)==1:
                raise TransientError()
            return "ok"
        self.assertEqual(retry_transient(fn,sleep=lambda _:None),"ok")
        self.assertEqual(len(calls),2)
    def test_retry_exhaustion(self):
        with self.assertRaises(TransientError):
            retry_transient(lambda: (_ for _ in ()).throw(TransientError()),attempts=2,sleep=lambda _:None)
    def test_no_retry_permanent(self):
        with self.assertRaises(ValueError):
            retry_transient(lambda: (_ for _ in ()).throw(ValueError()))
    def test_cli_plan(self):
        out=StringIO()
        with redirect_stdout(out):
            rc=main(["--workspace",str(self.root),"--config",str(self.path),"plan"])
        self.assertEqual(rc,0)
        self.assertEqual(json.loads(out.getvalue())["action"],"update")
    def test_cli_approval_gate(self):
        out=StringIO()
        with redirect_stdout(out):
            rc=main(["--workspace",str(self.root),"--config",str(self.path),"apply"])
        self.assertEqual(rc,3)
    def test_cli_apply(self):
        out=StringIO()
        with redirect_stdout(out):
            rc=main(["--workspace",str(self.root),"--config",str(self.path),"apply","--apply"])
        self.assertEqual(rc,0)
    def test_cli_missing_config(self):
        out=StringIO()
        with redirect_stdout(out):
            rc=main(["--workspace",str(self.root),"plan"])
        self.assertEqual(rc,2)

if __name__=="__main__":
    unittest.main()
\`\`\`

## Runbook and validation
\`\`\`bash
python -m compileall -q infra_cli.py test_infra_cli.py
python -m unittest -v test_infra_cli.py
mkdir -p ./lab-workspace
python infra_cli.py --workspace ./lab-workspace --config ./config.json plan
python infra_cli.py --workspace ./lab-workspace --config ./config.json apply
python infra_cli.py --workspace ./lab-workspace --config ./config.json apply --apply
python infra_cli.py --workspace ./lab-workspace --config ./config.json status
python infra_cli.py --workspace ./lab-workspace probe
\`\`\`
Windows: \`py -m unittest -v test_infra_cli.py\` and create the workspace with \`New-Item -ItemType Directory -Force lab-workspace\`.

### Incident drills
1. Path traversal; 2. Invalid state; 3. Invalid generation; 4. Oversized config; 5. Symlink attack; 6. Dry-run no mutation; 7. Approval missing; 8. Atomic write; 9. Idempotent replay; 10. Drift; 11. Safe subprocess; 12. Timeout validation; 13. Transient retry; 14. Retry exhaustion; 15. Permanent failure; 16. JSON output; 17. CLI exit code; 18. Disk-full write (guided); 19. Concurrent writers (guided); 20. Credentials in logs (guided).

### Operational runbooks
**Preflight:** verify scope, workspace, target, dry-run and approval. **Subprocess failure:** inspect sanitized exit code and actual state before retry. **Drift:** re-plan and reapprove changed state. **Secrets:** rotate exposed credentials and review audit logs. **Rollback:** restore previously verified desired state, validate checksum and SLO.

### CI template
\`\`\`yaml
name: chapter-081-infra-cli
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m unittest -v test_infra_cli.py
\`\`\`
Template only: extract source files, pin reviewed action SHAs and enable through approved CI.

### 100-point assessment
| Topic | Points |
|---|---:|
| argparse CLI and exit codes | 20 |
| subprocess safety | 15 |
| Configuration and path validation | 15 |
| Idempotency, dry-run and atomic replace | 20 |
| JSON logs and retries | 15 |
| Tests, incident drills and runbooks | 15 |

**Pass:** ≥90/100 and independently executed tests. Cross-process locking, fsync of the containing directory and production policy integration remain future hardening tasks.
