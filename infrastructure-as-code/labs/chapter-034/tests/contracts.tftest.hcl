variables {
  environment        = "dev"
  owner              = "platform-sre"
  network_cidr       = "10.44.0.0/24"
  database_replicas  = 2
  backup_enabled     = true
  encryption_enabled = true
  change_ticket      = "CHG-TEST-034"
}

run "dev_contracts" {
  command = plan

  assert {
    condition     = output.network_contract.schema_version == 1
    error_message = "network schema must be v1"
  }

  assert {
    condition     = output.database_contract.schema_version == 1
    error_message = "database schema must be v1"
  }

  assert {
    condition     = output.application_contract.schema_version == 1
    error_message = "application schema must be v1"
  }

  assert {
    condition     = output.database_contract.backup_enabled && output.database_contract.encryption_enabled
    error_message = "database backup and encryption required"
  }

  assert {
    condition     = output.change_ticket == "CHG-TEST-034"
    error_message = "audit ticket must be preserved"
  }
}
