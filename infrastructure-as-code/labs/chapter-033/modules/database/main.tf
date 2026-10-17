resource "terraform_data" "database" {
  input = {
    environment        = var.environment
    network_id         = var.network.id
    replicas           = var.replicas
    backup_enabled     = var.backup_enabled
    encryption_enabled = var.encryption_enabled
  }
  lifecycle {
    precondition {
      condition = var.network.schema_version == 1 && var.network.environment == var.environment
      error_message = "network contract mismatch"
    }
    precondition {
      condition = var.environment != "prod" || (var.replicas >= 3 && var.backup_enabled && var.encryption_enabled)
      error_message = "production requires three replicas, backup and encryption"
    }
  }
}
