"""Mock-only multi-cloud component. Synthetic resources are NOT cloud provider schemas."""
import pulumi

class SyntheticTarget(pulumi.CustomResource):
    def __init__(self, name, cloud, opts=None):
        super().__init__("iac:mock:Target", name, {"cloud": cloud, "encrypted": True}, opts)

class MultiCloudPlatform(pulumi.ComponentResource):
    def __init__(self, name, opts=None):
        super().__init__("iac:mock:MultiCloudPlatform", name, None, opts)
        self.aws = SyntheticTarget(name + "-aws", "aws", pulumi.ResourceOptions(parent=self, protect=True))
        self.azure = SyntheticTarget(name + "-azure", "azure", pulumi.ResourceOptions(parent=self, depends_on=[self.aws]))
        self.gcp = SyntheticTarget(name + "-gcp", "gcp", pulumi.ResourceOptions(parent=self, depends_on=[self.azure]))
        self.register_outputs({"aws_id": self.aws.id, "azure_id": self.azure.id, "gcp_id": self.gcp.id})
