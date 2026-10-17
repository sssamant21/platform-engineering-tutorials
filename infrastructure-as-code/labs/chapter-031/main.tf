module "network" {
  source      = "./modules/network"
  environment = var.environment
  cidr        = var.network_cidr
  owner       = var.owner
}

module "database" {
  source             = "./modules/database"
  environment        = var.environment
  network            = module.network.contract
  replicas           = var.database_replicas
  backup_enabled     = var.backup_enabled
  encryption_enabled = var.encryption_enabled
}

module "application" {
  source      = "./modules/application"
  environment = var.environment
  database    = module.database.contract
  owner       = var.owner
}

resource "terraform_data" "audit" {
  input = {
    change_ticket  = var.change_ticket
    environment    = var.environment
    application_id = module.application.contract.id
  }
}
