module "network" {
  source      = "./modules/network"
  environment = var.environment
  subnet_ids  = var.subnet_ids
}
module "database" {
  source              = "./modules/database"
  environment         = var.environment
  owner               = var.owner
  network             = module.network.contract
  replicas            = var.replicas
  backup_enabled      = var.backup_enabled
  encryption_enabled  = var.encryption_enabled
  deletion_protection = var.deletion_protection
}
resource "terraform_data" "application" {
  input = {
    environment   = var.environment
    database_name = module.database.contract.name
    release       = var.release
  }
  triggers_replace = var.release
  lifecycle {
    create_before_destroy = true
    postcondition {
      condition     = self.output.release != ""
      error_message = "release output must be nonempty"
    }
  }
}
resource "terraform_data" "monitoring" {
  input = {
    app_release = terraform_data.application.output.release
    owner       = var.owner
  }
}
resource "terraform_data" "audit" {
  input = {
    environment   = var.environment
    owner         = var.owner
    change_ticket = var.change_ticket
  }
  depends_on = [terraform_data.monitoring]
  lifecycle {
    prevent_destroy = true
  }
}
