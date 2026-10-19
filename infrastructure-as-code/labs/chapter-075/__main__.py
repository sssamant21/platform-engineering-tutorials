"""Mock-only Pulumi resource graph. Never run with real providers."""
import pulumi
from components import MultiCloudPlatform
platform = MultiCloudPlatform("ch075")
pulumi.export("awsId", platform.aws.id)
pulumi.export("azureId", platform.azure.id)
pulumi.export("gcpId", platform.gcp.id)
