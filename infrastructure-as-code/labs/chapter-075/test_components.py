"""Pulumi mocks: no AWS, Azure or GCP API calls."""
import unittest
import pulumi
from pulumi.runtime import Mocks, MockResourceArgs, MockCallArgs
from components import MultiCloudPlatform, SyntheticTarget

class MockCloud(Mocks):
    def new_resource(self, args: MockResourceArgs):
        return ("mock-" + args.name, args.inputs)
    def call(self, args: MockCallArgs):
        return {}

pulumi.runtime.set_mocks(MockCloud(), project="iac-ch075-pulumi", stack="dev", preview=False)

class ComponentTests(unittest.TestCase):
    def test_component_class(self):
        self.assertTrue(issubclass(MultiCloudPlatform, pulumi.ComponentResource))
    def test_child_class(self):
        self.assertTrue(issubclass(SyntheticTarget, pulumi.CustomResource))
    def test_three_children(self):
        p = MultiCloudPlatform("test")
        self.assertTrue(all([p.aws, p.azure, p.gcp]))
    @pulumi.runtime.test
    def test_aws_id(self):
        p = MultiCloudPlatform("check-aws")
        return p.aws.id.apply(lambda x: self.assertEqual(x, "mock-check-aws-aws"))
    @pulumi.runtime.test
    def test_azure_id(self):
        p = MultiCloudPlatform("check-azure")
        return p.azure.id.apply(lambda x: self.assertEqual(x, "mock-check-azure-azure"))
    @pulumi.runtime.test
    def test_gcp_id(self):
        p = MultiCloudPlatform("check-gcp")
        return p.gcp.id.apply(lambda x: self.assertEqual(x, "mock-check-gcp-gcp"))
if __name__ == "__main__":
    unittest.main()
