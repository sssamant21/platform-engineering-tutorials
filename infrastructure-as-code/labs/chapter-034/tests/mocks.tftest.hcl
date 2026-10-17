# Terraform 1.7+ mock provider and deterministic resource output override.
mock_provider "terraform" {}

variables {
  environment        = "dev"
  owner              = "platform-sre"
  network_cidr       = "10.44.0.0/24"
  database_replicas  = 2
  backup_enabled     = true
  encryption_enabled = true
  change_ticket      = "CHG-MOCK-034"
}

run "mocked_network_contract" {
  command = plan

  override_resource {
    target = module.network.terraform_data.network
    values = {
      id = "mock-network-034"
      output = {
        environment = "dev"
        cidr        = "10.44.0.0/24"
        owner       = "platform-sre"
        labels = {
          team = "platform"
          cost_center = "sandbox"
        }
      }
    }
  }

  assert {
    condition     = output.network_contract.id == "mock-network-034"
    error_message = "mock override must yield deterministic network ID"
  }

  assert {
    condition     = output.database_contract.network_id == "mock-network-034"
    error_message = "database must consume mocked network ID"
  }
}
