locals {
  enabled_services = { for name, svc in var.services : name => svc if svc.enabled }
  sorted_zones     = sort(distinct(var.zones))
  workload_rows = flatten([
    for name, svc in local.enabled_services : [
      for zone in local.sorted_zones : {
        key         = format("%s@%s", name, zone)
        name        = name
        zone        = zone
        tier        = svc.tier
        replicas    = svc.replicas
        environment = var.environment
        tags        = merge(var.tags, { environment = var.environment, owner = var.owner })
      }
    ]
  ])
  workloads = { for row in local.workload_rows : row.key => row }
  grouped_tiers = { for name, svc in local.enabled_services : svc.tier => name... }
}
resource "terraform_data" "workload" {
  for_each = local.workloads
  input    = each.value
}
resource "terraform_data" "audit" {
  input = {
    environment = var.environment
    owner       = var.owner
    addresses   = sort(keys(local.workloads))
    tiers       = local.grouped_tiers
  }
  depends_on = [terraform_data.workload]
}
