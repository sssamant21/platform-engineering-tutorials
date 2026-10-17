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
    tier           = var.database_tier
    replicas       = var.replicas
    backup_enabled = var.backup_enabled
  }
  lifecycle {
    precondition {
      condition     = var.environment != "prod" || (var.backup_enabled && var.replicas >= 3 && var.database_tier == "premium")
      error_message = "production requires backup, three replicas and premium tier"
    }
  }
}
resource "terraform_data" "application" {
  input = {
    environment = var.environment
    database_id = terraform_data.database.id
    owner       = var.owner
  }
}
