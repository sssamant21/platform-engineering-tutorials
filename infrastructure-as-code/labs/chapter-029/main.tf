resource "terraform_data" "network" {
  input = {
    environment = var.environment
    subnet      = "subnet-lab-${var.environment}"
    owner       = var.owner
  }
}
resource "terraform_data" "database" {
  input = {
    environment    = var.environment
    subnet         = terraform_data.network.output.subnet
    replicas       = var.replicas
    backup_enabled = var.backup_enabled
  }
  lifecycle {
    precondition {
      condition     = var.environment != "prod" || (var.backup_enabled && var.replicas >= 3)
      error_message = "production requires backup and at least three replicas"
    }
  }
}
resource "terraform_data" "application" {
  input = {
    environment   = var.environment
    database_name = terraform_data.database.output.environment
    change_ticket = var.change_ticket
  }
}
