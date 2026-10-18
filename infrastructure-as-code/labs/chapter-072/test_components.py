"""Pulumi mocked-resource unit tests: no cloud API calls."""
import unittest
import pulumi
from pulumi.runtime import Mocks, MockResourceArgs, MockCallArgs
from components import LabService

class LabMocks(Mocks):
    def new_resource(self, args: MockResourceArgs):
        return ("mock-" + args.name, args.inputs)
    def call(self, args: MockCallArgs):
        return {}

pulumi.runtime.set_mocks(LabMocks(), project="iac-ch072-pulumi", stack="dev", preview=False)

class ComponentTests(unittest.TestCase):
    def test_component_type(self):
        self.assertTrue(issubclass(LabService, pulumi.ComponentResource))
    def test_child_type(self):
        from components import LabChild
        self.assertTrue(issubclass(LabChild, pulumi.CustomResource))
    def test_component_children(self):
        service = LabService("example")
        self.assertIsNotNone(service.primary)
        self.assertIsNotNone(service.monitor)
    @pulumi.runtime.test
    def test_mock_primary_id(self):
        service = LabService("primary-check")
        def verify(value):
            self.assertEqual(value, "mock-primary-check-primary")
        return service.primary.id.apply(verify)
    @pulumi.runtime.test
    def test_mock_monitor_id(self):
        service = LabService("monitor-check")
        def verify(value):
            self.assertEqual(value, "mock-monitor-check-monitor")
        return service.monitor.id.apply(verify)

if __name__ == "__main__":
    unittest.main()
