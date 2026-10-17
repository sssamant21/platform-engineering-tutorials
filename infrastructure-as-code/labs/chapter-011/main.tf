locals {
  environment = lower(var.environment)
  service = lower(var.service)
  tier = var.environment == "prod" ? "critical" : "standard"
  dns_name = "${local.service}.${local.environment}.internal"
  zone_names = [for z in var.zones : lower(trimspace(z))]
  zone_index = { for z in local.zone_names : z => "enabled" }
  metadata = {
    owner = var.owner
    environment = local.environment
    service = local.service
    tier = local.tier
    replicas = var.replicas
    dns_name = local.dns_name
    zones = local.zone_index
  }
}
resource "terraform_data" "metadata" {
  input = local.metadata
}
resource "terraform_data" "consumer" {
  input = {
    source_service = terraform_data.metadata.output.service
    source_tier = terraform_data.metadata.output.tier
  }
}
