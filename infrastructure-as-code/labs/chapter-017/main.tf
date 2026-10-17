locals {
  canonical_service = lower(trimspace(var.service))
  is_production = var.environment == "prod"
  active_services = { for name, spec in var.services : name => spec if spec.enabled }
  service_names = sort(keys(local.active_services))
  tags = merge(var.tags, { environment = var.environment, owner = var.owner, application = local.canonical_service })
  workload_records = { for name, spec in local.active_services : name => {
    name = format("%s-%s-%s", local.canonical_service, var.environment, name)
    tier = spec.tier
    replicas = local.is_production ? max(spec.replicas, 3) : spec.replicas
    tags = local.tags
  } }
}
resource "terraform_data" "service" {
  for_each = local.workload_records
  input = each.value
}
resource "terraform_data" "audit" {
  input = {
    environment = var.environment
    service_names = local.service_names
    service_count = length(local.service_names)
    owner = var.owner
  }
  depends_on = [terraform_data.service]
}
