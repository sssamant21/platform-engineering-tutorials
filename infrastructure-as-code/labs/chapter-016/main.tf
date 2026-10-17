locals {
  normalized_service = lower(var.service)
  zone_index         = { for zone in var.zones : lower(zone) => "enabled" }
  metadata = {
    environment = var.environment
    service     = local.normalized_service
    owner       = var.owner
    replicas    = var.replicas
    zones       = local.zone_index
    tags        = var.tags
    database    = var.database
  }
}
resource "terraform_data" "input_contract" {
  input = local.metadata
}
check "production_database_safety" {
  assert {
    condition     = var.environment != "prod" || (var.database.encrypted && var.database.backup_enabled && var.database.replica_count >= 2)
    error_message = "Production database requires encryption, backups and at least two replicas."
  }
}
