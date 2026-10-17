environment = "dev"
owner = "platform-sre"
change_ticket = "CHG-DEMO-DEV"
zones = ["a", "b"]
services = {
  api = { replicas = 2, enabled = true, tier = "frontend" }
  worker = { replicas = 2, enabled = true, tier = "backend" }
}
database_backup_enabled = true
database_encrypted = true
database_deletion_protection = true
database_replicas = 2
tags = { managed_by = "terraform", cost_center = "lab" }
