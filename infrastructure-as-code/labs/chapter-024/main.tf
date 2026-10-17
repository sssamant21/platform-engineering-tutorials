locals {
  production = var.environment == "prod"
  safe = !local.production || (var.replicas >= 3 && var.backup_enabled && var.encryption_enabled && var.deletion_protection)
}
resource "terraform_data" "service" {
  input = {
    environment = var.environment
    release = var.release
    replicas = var.replicas
    owner = var.owner
  }
  triggers_replace = var.release
  lifecycle {
    create_before_destroy = true
    precondition {
      condition = local.safe
      error_message = "production requires 3+ replicas, backups, encryption and deletion protection"
    }
    postcondition {
      condition = self.output.release != ""
      error_message = "release must not be empty"
    }
  }
}
resource "terraform_data" "audit" {
  input = {
    service_id = terraform_data.service.id
    owner = var.owner
    change_ticket = var.change_ticket
  }
  lifecycle {
    prevent_destroy = true
  }
}
