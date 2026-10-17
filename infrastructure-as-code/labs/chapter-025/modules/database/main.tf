resource "terraform_data" "contract" {
  input = {
    schema_version       = 1
    name                 = "database-${var.environment}"
    environment          = var.environment
    owner                = var.owner
    network              = { primary = var.network.primary, secondary = var.network.secondary }
    replicas             = var.replicas
    backup_enabled       = var.backup_enabled
    encryption_enabled   = var.encryption_enabled
    deletion_protection  = var.deletion_protection
  }
  lifecycle {
    precondition {
      condition     = var.network.schema_version == 1 && var.network.environment == var.environment
      error_message = "network contract version/environment mismatch"
    }
    precondition {
      condition     = var.environment != "prod" || (var.replicas >= 3 && var.backup_enabled && var.encryption_enabled && var.deletion_protection)
      error_message = "production requires 3+ replicas, backup, encryption and deletion protection"
    }
  }
}
