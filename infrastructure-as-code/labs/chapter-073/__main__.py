"""No-resource Pulumi configuration lab. No cloud API calls."""
import pulumi
config = pulumi.Config()
environment = config.get("environment") or "lab"
if environment not in ("lab", "dev"):
    raise ValueError("Only lab/dev allowed")
pulumi.export("environment", environment)
