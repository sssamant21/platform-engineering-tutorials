"""Only for a mocked unit test; do not run pulumi up against real providers."""
import pulumi
from components import LabService

service = LabService("chapter072")
pulumi.export("primaryId", service.primary.id)
pulumi.export("monitorId", service.monitor.id)
