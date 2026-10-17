variables {
  environment        = "dev"
  owner              = "platform-sre"
  network_cidr       = "10.45.0.0/24"
  database_replicas  = 2
  backup_enabled     = true
  encryption_enabled = true
  change_ticket      = "CHG-TEST-035"
}

run "reject_zero_replicas" {
  command = plan
  variables {
    database_replicas = 0
  }
  expect_failures = [var.database_replicas]
}

run "reject_bad_cidr" {
  command = plan
  variables {
    network_cidr = "not-a-cidr"
  }
  expect_failures = [var.network_cidr]
}

run "reject_prod_backup_disabled" {
  command = plan
  variables {
    environment       = "prod"
    database_replicas = 3
    backup_enabled    = false
  }
  expect_failures = [module.database.terraform_data.database]
}

run "reject_prod_underreplicated" {
  command = plan
  variables {
    environment       = "prod"
    database_replicas = 1
  }
  expect_failures = [module.database.terraform_data.database]
}
