variables {
  environment        = "dev"
  owner              = "platform-sre"
  network_cidr       = "10.45.0.0/24"
  database_replicas  = 2
  backup_enabled     = true
  encryption_enabled = true
  change_ticket      = "CHG-TEST-035"
}

run "module_contracts" {
  command = plan
  assert {
    condition     = output.network_contract.schema_version == 1
    error_message = "network contract version must be one"
  }
  assert {
    condition     = output.database_contract.schema_version == 1
    error_message = "database contract version must be one"
  }
  assert {
    condition     = output.application_contract.schema_version == 1
    error_message = "application contract version must be one"
  }
  assert {
    condition     = output.database_contract.backup_enabled && output.database_contract.encryption_enabled
    error_message = "backup and encryption must remain enabled"
  }
  assert {
    condition     = output.change_ticket == "CHG-TEST-035"
    error_message = "change ticket must propagate to audit resource"
  }
}
