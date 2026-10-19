"""Optional local Pulumi Automation API preview; no update or destroy."""
import os
from pathlib import Path

import pulumi.automation as auto

root = Path(__file__).resolve().parent
backend = os.environ.get("PULUMI_BACKEND_URL", "")
if not backend.startswith("file://") or not backend.endswith("/.pulumi-state"):
    raise SystemExit("Require isolated local PULUMI_BACKEND_URL ending in /.pulumi-state")
if not os.environ.get("PULUMI_CONFIG_PASSPHRASE"):
    raise SystemExit("Require disposable lab PULUMI_CONFIG_PASSPHRASE")
stack = auto.create_or_select_stack(stack_name="dev", work_dir=str(root))
stack.set_config("environment", auto.ConfigValue(value="lab"))
print("Preview only; no up or destroy")
result = stack.preview()
print("Preview completed:", result.change_summary)
