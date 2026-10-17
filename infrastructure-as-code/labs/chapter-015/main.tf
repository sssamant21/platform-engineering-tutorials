locals {
  owner = "platform-sre"
  services = {
    api    = "frontend"
    worker = "backend"
  }
}
resource "terraform_data" "seed" {
  input = {
    environment = var.environment
    replicas    = var.replicas
    owner       = local.owner
  }
}
resource "terraform_data" "service" {
  for_each = local.services
  input = {
    name        = each.key
    tier        = each.value
    environment = terraform_data.seed.output.environment
    owner       = local.owner
  }
}
resource "terraform_data" "audit" {
  input = {
    service_names = sort(keys(terraform_data.service))
    environment   = terraform_data.seed.output.environment
    owner         = local.owner
  }
  depends_on = [terraform_data.service]
}
