"""Local-only Pulumi resource; no cloud providers or remote targets."""
import pulumi
import pulumi_command as command

cfg = pulumi.Config()
environment = cfg.get("environment") or "lab"
if environment not in ("lab", "dev"):
    raise ValueError("Only lab/dev environments are allowed")

# This is a local command resource. Never pass credentials into shell arguments.
marker = command.local.Command(
    "local-marker",
    create="mkdir -p sandbox && printf 'chapter071-local-only\\n' > sandbox/marker.txt",
    delete="rm -f sandbox/marker.txt",
    triggers=[environment],
)

pulumi.export("environment", environment)
pulumi.export("marker", marker.stdout.apply(lambda _: "sandbox/marker.txt"))
