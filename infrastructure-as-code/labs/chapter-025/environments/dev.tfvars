environment         = "dev"
owner               = "platform-sre"
change_ticket       = "CHG-DEMO-DEV"
subnet_ids          = { primary = "subnet-lab-dev-a", secondary = "subnet-lab-dev-b" }
replicas            = 2
backup_enabled      = true
encryption_enabled  = true
deletion_protection = true
release             = "v1"
