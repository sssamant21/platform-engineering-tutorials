environment = "prod"
owner = "dbre-team"
change_ticket = "CHG-DEMO-PROD"
zones = ["a", "b", "c"]
services = {
  api = { replicas = 3, enabled = true, tier = "frontend" }
  worker = { replicas = 3, enabled = true, tier = "backend" }
}
database_backup_enabled = true
database_encrypted = true
database_deletion_protection = true
database_replicas = 3
tags = { managed_by = "terraform", cost_center = "demo-prod" }
