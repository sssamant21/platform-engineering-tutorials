"""Mock-only Pulumi component architecture; not cloud provider code."""
import pulumi

class LabChild(pulumi.CustomResource):
    def __init__(self, name, properties, opts=None):
        super().__init__("iac:lab:Child", name, properties, opts)

class LabService(pulumi.ComponentResource):
    def __init__(self, name, opts=None):
        super().__init__("iac:lab:Service", name, None, opts)
        self.primary = LabChild(
            name + "-primary",
            {"kind": "stateful", "encrypted": True},
            pulumi.ResourceOptions(parent=self, protect=True),
        )
        self.monitor = LabChild(
            name + "-monitor",
            {"kind": "monitoring", "encrypted": True},
            pulumi.ResourceOptions(parent=self, depends_on=[self.primary]),
        )
        self.register_outputs({
            "primary_id": self.primary.id,
            "monitor_id": self.monitor.id,
        })
