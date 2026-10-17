environment         = "prod"
owner               = "dbre-team"
change_ticket       = "CHG-DEMO-PROD"
subnet_ids          = { primary = "subnet-lab-prod-a", secondary = "subnet-lab-prod-b" }
replicas            = 3
backup_enabled      = true
encryption_enabled  = true
deletion_protection = true
release             = "v1"
