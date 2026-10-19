"""No-resource Pulumi stack for local Automation API preview."""
import pulumi
cfg = pulumi.Config()
environment = cfg.get("environment") or "lab"
if environment not in ("lab", "dev"):
    raise ValueError("Only lab/dev")
pulumi.export("environment", environment)
