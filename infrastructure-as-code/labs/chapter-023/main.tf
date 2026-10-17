module "network" {
  source = "./modules/network"
  environment = var.environment
  subnet_ids = var.subnet_ids
}
module "database" {
  source = "./modules/database"
  environment = var.environment
  owner = var.owner
  network = module.network.contract
  backup_enabled = var.database_backup_enabled
  encrypted = var.database_encrypted
}
resource "terraform_data" "application" {
  input = {
    environment = var.environment
    database_name = module.database.contract.name
    network_primary = module.database.contract.network.primary
    owner = var.owner
    change_ticket = var.change_ticket
  }
}
