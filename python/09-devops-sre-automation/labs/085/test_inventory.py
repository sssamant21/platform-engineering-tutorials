"""Offline multicloud inventory tests; no credentials or network."""
import json
from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from inventory import InventoryError,Record,aws_ec2,azure_resources,gcp_projects,bounded,offline_fake,main

class InventoryTests(unittest.TestCase):
    def test_aws_pagination(self):
        client=Mock()
        client.get_paginator.return_value.paginate.return_value=[
            {"Reservations":[{"Instances":[{"InstanceId":"i-a"},{"InstanceId":"i-b"}]}]},
            {"Reservations":[{"Instances":[{"InstanceId":"i-c"}]}]}]
        result=bounded(aws_ec2(client,"us-east-1"))
        self.assertEqual(len(result["records"]),3)
        self.assertFalse(result["partial"])
        client.get_paginator.assert_called_once_with("describe_instances")
    def test_aws_invalid_id(self):
        client=Mock()
        client.get_paginator.return_value.paginate.return_value=[
            {"Reservations":[{"Instances":[{"InstanceId":"bad"}]}]}]
        with self.assertRaises(InventoryError):
            list(aws_ec2(client,"us-east-1"))
    def test_aws_invalid_region(self):
        with self.assertRaises(ValueError):
            list(aws_ec2(Mock(),"../prod"))
    def test_azure_pager(self):
        client=Mock()
        client.resources.list.return_value=[SimpleNamespace(id="/subscriptions/s/rg/r",type="Microsoft.Resources/resourceGroups")]
        self.assertEqual(bounded(azure_resources(client,"s"))["records"][0]["provider"],"azure")
    def test_azure_invalid_object(self):
        client=Mock()
        client.resources.list.return_value=[SimpleNamespace(id=None,type="vm")]
        with self.assertRaises(InventoryError):
            list(azure_resources(client,"s"))
    def test_azure_invalid_scope(self):
        with self.assertRaises(ValueError):
            list(azure_resources(Mock(),""))
    def test_gcp_pager(self):
        client=Mock()
        client.search_projects.return_value=[SimpleNamespace(name="projects/123")]
        result=bounded(gcp_projects(client,"123456"))
        self.assertEqual(result["records"][0]["resource_id"],"projects/123")
        self.assertIn("parent.id:123456",client.search_projects.call_args.kwargs["request"]["query"])
    def test_gcp_invalid_scope(self):
        with self.assertRaises(ValueError):
            list(gcp_projects(Mock(),"org/123"))
    def test_gcp_invalid_object(self):
        client=Mock()
        client.search_projects.return_value=[SimpleNamespace(name="bad")]
        with self.assertRaises(InventoryError):
            list(gcp_projects(client,"123"))
    def test_dedup(self):
        item=Record("aws","us-east-1","ec2-instance","i-1")
        result=bounded([item,item,item],1)
        self.assertEqual(len(result["records"]),1)
        self.assertFalse(result["partial"])
    def test_partial(self):
        rows=[Record("aws","us-east-1","ec2-instance",f"i-{i}") for i in range(3)]
        result=bounded(rows,2)
        self.assertTrue(result["partial"])
        self.assertEqual(len(result["records"]),2)
    def test_exact_budget(self):
        rows=[Record("aws","us-east-1","ec2-instance",f"i-{i}") for i in range(2)]
        self.assertFalse(bounded(rows,2)["partial"])
    def test_invalid_budget(self):
        with self.assertRaises(ValueError):
            bounded([],0)
    def test_all_fakes(self):
        for provider in ("aws","azure","gcp"):
            with self.subTest(provider=provider):
                self.assertEqual(len(bounded(offline_fake(provider))["records"]),2)
    def test_cli_dry_run(self):
        output=StringIO()
        with redirect_stdout(output):
            rc=main(["--provider","aws","--dry-run"])
        self.assertEqual(rc,0)
        self.assertEqual(json.loads(output.getvalue())["network_calls"],0)
    def test_cli_partial(self):
        output=StringIO()
        with redirect_stdout(output):
            rc=main(["--provider","gcp","--max-records","1"])
        self.assertEqual(rc,0)
        self.assertTrue(json.loads(output.getvalue())["partial"])
    def test_unknown_provider_fixture(self):
        with self.assertRaises(ValueError):
            list(offline_fake("other"))

if __name__=="__main__":
    unittest.main()
