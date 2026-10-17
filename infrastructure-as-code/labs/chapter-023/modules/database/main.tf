resource "terraform_data" "contract" {
  input = {
    schema_version = 1
    name = "database-${var.environment}"
    environment = var.environment
    owner = var.owner
    network = { primary = var.network.primary, secondary = var.network.secondary }
    backup_enabled = var.backup_enabled
    encrypted = var.encrypted
  }
  lifecycle {
    precondition {
      condition = var.network.environment == var.environment && var.network.schema_version == 1
      error_message = "network contract version and environment must match database module"
    }
    precondition {
      condition = var.environment != "prod" || (var.backup_enabled && var.encrypted)
      error_message = "production database requires backup and encryption"
    }
  }
}
