locals {
  is_production = var.environment == "prod"
  display_label = var.display_name != null && trimspace(var.display_name) != "" ? trimspace(var.display_name) : var.service
  capacity = local.is_production ? max(var.replicas, 3) : var.replicas
  db_engine = try(var.database.engine, "postgres")
  db_backup = var.database.backup_enabled == null ? var.backup_enabled : var.database.backup_enabled
  db_replicas = var.database.replicas == null ? var.replicas : var.database.replicas
  record = {
    environment = var.environment
    service = var.service
    display_label = local.display_label
    owner = var.owner
    change_ticket = var.change_ticket
    replicas = local.capacity
    database = {
      engine = local.db_engine
      backup_enabled = local.db_backup
      replicas = local.db_replicas
      encryption_enabled = var.encryption_enabled
      deletion_protection = var.deletion_protection
    }
  }
}
resource "terraform_data" "defensive_contract" {
  input = local.record
  lifecycle {
    precondition {
      condition = !local.is_production || (var.replicas >= 3 && local.db_replicas >= 3 && local.db_backup && var.encryption_enabled && var.deletion_protection)
      error_message = "Production requires 3+ replicas, backups, encryption and deletion protection"
    }
  }
}
