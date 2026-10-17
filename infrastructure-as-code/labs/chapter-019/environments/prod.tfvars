environment = "prod"
service = "patient-api"
owner = "dbre-team"
change_ticket = "CHG-DEMO-PROD"
replicas = 3
backup_enabled = true
encryption_enabled = true
deletion_protection = true
database = { engine = "postgres", backup_enabled = true, replicas = 3 }
