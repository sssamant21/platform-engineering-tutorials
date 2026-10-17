locals {
  service_names = sort(keys(var.services))
}
resource "terraform_data" "seed" {
  input = {
    environment = var.environment
    chapter     = "012"
  }
}
resource "terraform_data" "service" {
  for_each = var.services
  input = {
    name        = each.key
    owner       = each.value.owner
    tier        = each.value.tier
    environment = terraform_data.seed.output.environment
  }
}
resource "terraform_data" "audit" {
  input = {
    service_names = local.service_names
    environment   = terraform_data.seed.output.environment
    owner         = "platform-sre"
  }
  depends_on = [terraform_data.service]
  lifecycle {
    prevent_destroy = true
  }
}
