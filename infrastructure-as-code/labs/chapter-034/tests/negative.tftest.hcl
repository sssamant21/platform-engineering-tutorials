variables {
  environment        = "dev"
  owner              = "platform-sre"
  network_cidr       = "10.44.0.0/24"
  database_replicas  = 2
  backup_enabled     = true
  encryption_enabled = true
  change_ticket      = "CHG-TEST-034"
}

run "reject_zero_replicas" {
  command = plan
  variables {
    database_replicas = 0
  }
  expect_failures = [var.database_replicas]
}

run "reject_invalid_cidr" {
  command = plan
  variables {
    network_cidr = "not-a-cidr"
  }
  expect_failures = [var.network_cidr]
}

run "reject_prod_without_backup" {
  command = plan
  variables {
    environment    = "prod"
    backup_enabled = false
    database_replicas = 3
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
