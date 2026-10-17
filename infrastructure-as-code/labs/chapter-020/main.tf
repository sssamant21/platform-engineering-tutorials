locals {
  is_production = var.environment == "prod"
  enabled_services = { for name, svc in var.services : name => svc if svc.enabled }
  zone_names = sort(distinct(var.zones))
  rows = flatten([
    for name, svc in local.enabled_services : [
      for zone in local.zone_names : {
        key = format("%s@%s", name, zone)
        name = name
        zone = zone
        tier = svc.tier
        replicas = svc.replicas
        environment = var.environment
        tags = merge(var.tags, { owner = var.owner, environment = var.environment })
      }
    ]
  ])
  workloads = { for row in local.rows : row.key => row }
  database = {
    replicas = var.database_replicas
    backup_enabled = var.database_backup_enabled
    encrypted = var.database_encrypted
    deletion_protection = var.database_deletion_protection
  }
}
resource "terraform_data" "workload" {
  for_each = local.workloads
  input = each.value
  lifecycle {
    precondition {
      condition = !local.is_production || each.value.replicas >= 3
      error_message = "production workloads require at least three replicas"
    }
  }
}
resource "terraform_data" "audit" {
  input = {
    environment = var.environment
    owner = var.owner
    change_ticket = var.change_ticket
    workload_keys = sort(keys(local.workloads))
    database = local.database
  }
  depends_on = [terraform_data.workload]
  lifecycle {
    precondition {
      condition = !local.is_production || (var.database_replicas >= 3 && var.database_backup_enabled && var.database_encrypted && var.database_deletion_protection)
      error_message = "production database requires three replicas, backup, encryption and deletion protection"
    }
  }
}
